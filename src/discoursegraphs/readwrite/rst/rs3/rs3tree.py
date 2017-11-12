#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Arne Neumann <discoursegraphs.programming@arne.cl>

"""This module converts .rs3 files into `NLTK ParentedTree`s."""

from collections import defaultdict
import textwrap
from operator import methodcaller

from lxml import etree

from discoursegraphs.readwrite.tree import t
from discoursegraphs.readwrite.rst.rs3 import extract_relationtypes


class NoRootError(ValueError):
    """An RST Tree with multiple nodes without an ancestor."""
    pass


class TooManyChildrenError(ValueError):
    """An RST node with more child nodes than the theory allows."""
    pass


class TooFewChildrenError(ValueError):
    """An RST node with less child nodes than the theory allows."""
    pass


class RSTTree(object):
    """An RSTTree is a DGParentedTree representation of an .rs3 file."""
    def __init__(self, rs3_file, word_wrap=0, debug=False):
        self.child_dict, self.elem_dict, self.edus = get_rs3_data(rs3_file, word_wrap=word_wrap)
        self.edu_set = set(self.edus)
        self.tree = self.dt(debug=debug)

    def _repr_png_(self):
        """This PNG representation will be automagically used inside
        IPython notebooks.
        """
        return self.tree._repr_png_()

    def __str__(self):
        return self.tree.__str__()

    def pretty_print(self):
        """Return a pretty-printed representation of the RSTTree."""
        return self.tree.pretty_print()

    def __getitem__(self, key):
        return self.tree.__getitem__(key)

    def dt(self, start_node=None, debug=False):
        """main method to create an RSTTree from the output of get_rs3_data().

        TODO: add proper documentation
        """
        if start_node is None:
            return self.root2tree(start_node=start_node, debug=debug)

        elem_id = start_node
        if elem_id not in self.elem_dict:
            return []

        elem = self.elem_dict[elem_id]
        elem_type = elem['element_type']

        assert elem_type in ('segment', 'group')

        if elem_type == 'segment':
            return self.segment2tree(
                elem_id, elem, elem_type, start_node=start_node, debug=debug)

        else:
            return self.group2tree(
                elem_id, elem, elem_type, start_node=start_node, debug=debug)

    def root2tree(self, start_node=None, debug=False):
        root_nodes = self.child_dict[start_node]
        if len(root_nodes) == 1:
            return self.dt(start_node=root_nodes[0], debug=debug)
        elif len(root_nodes) > 1:
            # An undesired, but common case (at least in the PCC corpus).
            # This happens if there's one EDU not to connected to the rest
            # of the tree (e.g. a headline). We will just make all 'root'
            # nodes part of a multinuc relation called 'virtual-root'.
            root_subtrees = [self.dt(start_node=root_id, debug=debug)
                             for root_id in root_nodes]
            return t('virtual-root', [('N', sub) for sub in root_subtrees])
        else:
            return t('')

    def group2tree(self, elem_id, elem, elem_type, start_node=None, debug=False):
        if elem['reltype'] == 'rst':
            # this elem is the S in an N-S relation

            if len(self.child_dict[elem_id]) == 1:
                # this elem is the S in an N-S relation, but it's also the root of
                # another N-S relation
                subtree_id = self.child_dict[elem_id][0]
                subtree = self.dt(start_node=subtree_id, debug=debug)

            else:
                assert len(self.child_dict[elem_id]) > 1
                # this elem is the S in an N-S relation, but it's also the root of
                # a multinuc relation
                subtrees = [self.dt(start_node=c, debug=debug)
                            for c in self.child_dict[elem_id]]
                first_child_id = self.child_dict[elem_id][0]
                subtrees_relname = self.elem_dict[first_child_id]['relname']

                subtree = t(subtrees_relname, subtrees, debug=debug, root_id=elem_id)

            return t('S', subtree, debug=debug, root_id=elem_id)

        elif elem['reltype'] == 'multinuc':
            # this elem is one of several Ns in a multinuc relation

    #             assert len(child_dict[elem_id]) == 1
    #             child_id = child_dict[elem_id][0]
    #             subtree = dt(child_dict, elem_dict, ordered_edus, start_node=child_id, debug=debug)
            subtrees = [self.dt(start_node=c, debug=debug)
                        for c in self.child_dict[elem_id]]
            return t('N', subtrees, debug=debug, root_id=elem_id)

        else:
            assert elem.get('reltype') in ('', 'span'), \
                "Unexpected combination: elem_type '%s' and reltype '%s'" \
                    % (elem_type, elem['reltype'])

            # this elem is the N in an N-S relation
            if elem['group_type'] == 'multinuc':
                # this elem is also the 'root node' of a multinuc relation
                child_ids = self.child_dict[elem_id]
                multinuc_child_ids = [c for c in child_ids
                                      if self.elem_dict[c]['reltype'] == 'multinuc']
                multinuc_relname = self.elem_dict[multinuc_child_ids[0]]['relname']
                multinuc_subtree = t(multinuc_relname, [
                    self.dt(start_node=mc, debug=debug)
                    for mc in multinuc_child_ids], root_id=elem_id)

                other_child_ids = [c for c in child_ids
                                   if c not in multinuc_child_ids]

                if not other_child_ids:
                    # this elem is only the head of a multinuc relation
                    # TODO: does this make sense / is this ever reached?
                    return multinuc_subtree

                elif len(other_child_ids) == 1:
                    nuc_tree = t('N', multinuc_subtree, debug=debug, root_id=elem_id)

                    satellite_id = other_child_ids[0]
                    satellite_elem = self.elem_dict[satellite_id]
                    sat_subtree = self.dt(start_node=satellite_id, debug=debug)

                    return self.get_ordered_subtree(nuc_tree, sat_subtree, elem_id, satellite_id)

                else:  #len(other_child_ids) > 1
                    raise TooManyChildrenError(
                        "A multinuc group (%s) should not have > 1 non-multinuc children: %s" \
                            % (elem_id, other_child_ids))

            else:
                #~ assert elem['group_type'] == 'span', \
                    #~ "Unexpected group_type '%s'" % elem['group_type']
                if len(self.child_dict[elem_id]) == 1:
                    # this span at the top of a tree was only added for visual purposes
                    child_id = self.child_dict[elem_id][0]
                    return self.dt(start_node=child_id, debug=debug)

                elif len(self.child_dict[elem_id]) == 2:
                    # this elem is the N of an N-S relation (child: S), but is also
                    # a span over another relation (child: N)
                    children = {}
                    for child_id in self.child_dict[elem_id]:
                        children[self.elem_dict[child_id]['nuclearity']] = child_id

                    satellite_id = children['satellite']
                    satellite_elem = self.elem_dict[satellite_id]
                    relname = satellite_elem['relname']

                    sat_subtree = self.dt(start_node=children['satellite'], debug=debug)
                    nuc_subtree = self.dt(start_node=children['nucleus'], debug=debug)
                    nuc_tree = t('N'.format(elem_id), nuc_subtree, debug=debug, root_id=elem_id)

                    return self.get_ordered_subtree(
                        nuc_tree, sat_subtree,
                        nuc_id=children['nucleus'], sat_id=children['satellite'])

                elif len(self.child_dict[elem_id]) > 2:
                    raise TooManyChildrenError(
                        "A span group ('%s') should not have > 2 children: %s" \
                            % (elem_id, self.child_dict[elem_id]))
                else: #len(child_dict[elem_id]) == 0
                    raise TooFewChildrenError(
                        "A span group ('%s)' should have at least 1 child: %s" \
                            % (elem_id, self.child_dict[elem_id]))

    def segment2tree(self, elem_id, elem, elem_type, start_node=None, debug=False):
        if elem['reltype'] == 'rst':
            # this elem is the S in an N-S relation
            assert elem_id not in self.child_dict, \
                "A satellite segment (%s) should not have children: %s" \
                    % (elem_id, self.child_dict[elem_id])
            return t('S', elem['text'], debug=debug, root_id=elem_id)

        elif elem['reltype'] == 'multinuc':
            # this elem is one of several Ns in a multinuc relation
            assert elem_id not in self.child_dict, \
                "A multinuc segment (%s) should not have children: %s" \
                    % (elem_id, self.child_dict[elem_id])
            return t('N', elem['text'], debug=debug, root_id=elem_id)

        elif elem['reltype'] == 'span':
            # this elem is the N in an N-S relation
            nuc_tree = t('N', elem['text'], debug=debug, root_id=elem_id)

            assert len(self.child_dict[elem_id]) == 1, \
                "A span segment (%s) should have one child: %s" % (elem_id, self.child_dict[elem_id])
            satellite_id = self.child_dict[elem_id][0]
            sat_subtree = self.dt(start_node=satellite_id, debug=debug)

            return self.get_ordered_subtree(nuc_tree, sat_subtree, elem_id, satellite_id)

        if elem['nuclearity'] == 'root':
            assert not elem['reltype'], \
                "A root segment must not have a parent"

            if not self.child_dict.has_key(elem_id):
                # a root segment without any children (e.g. a headline in PCC)
                return t(elem['text'], debug=debug, root_id=elem_id)

            elif len(self.child_dict[elem_id]) == 1:
                # this elem is the N in an N-S relation
                nuc_tree = t('N', elem['text'], debug=debug, root_id=elem_id)

                sat_id = self.child_dict[elem_id][0]
                sat_tree = self.dt(start_node=sat_id, debug=debug)

                return self.get_ordered_subtree(nuc_tree, sat_tree, elem_id, sat_id)

            elif len(self.child_dict[elem_id]) == 2:
                # this elem is the N in an S-N-S schema
                raise NotImplementedError("Can't handle schemas, yet")

            else:
                raise NotImplementedError("Root segment has more than two children")

    def get_ordered_subtree(self, nuc_tree, sat_tree, nuc_id, sat_id):
        nuc_pos = self.get_position(nuc_id)
        sat_pos = self.get_position(sat_id)
        if  nuc_pos < sat_pos:
            subtrees = [nuc_tree, sat_tree]
        else:
            subtrees = [sat_tree, nuc_tree]

        relname = self.elem_dict[sat_id]['relname']
        return t(relname, subtrees)

    def get_position(self, node_id):
        """Get the position of a node in an RST tree to be constructed.

        TODO: add proper documentation
        """
        if node_id in self.edu_set:
            return self.edus.index(node_id)

        return min(self.get_position(child_node_id)
                   for child_node_id in self.child_dict[node_id])

    def sort_subtrees(self, *subtrees):
        return sorted(subtrees, key=methodcaller('get_position', self))


def get_rs3_data(rs3_file, word_wrap=0):
    """helper function to build RSTTrees: data on parent-child relations
    and node attributes.

    TODO: add proper documentation
    """
    rs3_etree = etree.parse(rs3_file)
    reltypes = extract_relationtypes(rs3_etree)
    elements = defaultdict(lambda: defaultdict(str))
    children = defaultdict(list)
    ordered_edus = []

    for elem in rs3_etree.iter('segment', 'group'):
        elem_id = elem.attrib['id']
        parent_id = elem.attrib.get('parent')
        elements[elem_id]['parent'] = parent_id
        children[parent_id].append(elem_id)

        relname = elem.attrib.get('relname')
        elements[elem_id]['relname'] = relname
        if relname is None:
            # Nodes without a parent have no relname attribute.
            # They might well the N of a relation.
            elements[elem_id]['nuclearity'] = 'root'
        else:
            reltype = reltypes.get(relname, 'span')
            elements[elem_id]['reltype'] = reltype
            if reltype == 'rst':
                # this elem is the S of an N-S relation, its parent is the N
                elements[elem_id]['nuclearity'] = 'satellite'
            elif reltype == 'multinuc':
                # this elem is one of several Ns of a multinuc relation.
                # its parent is the multinuc relation node.
                elements[elem_id]['nuclearity'] = 'nucleus'
            elif reltype == 'span':
                # this elem is the N of an N-S relation, its parent is a span
                elements[elem_id]['nuclearity'] = 'nucleus'
            else:
                raise NotImplementedError("Unknown reltype: {}".format(reltypes[relname]))

        elem_type = elem.tag
        elements[elem_id]['element_type'] = elem_type

        if elem_type == 'segment':
            edu_text = elem.text.strip()
            if word_wrap != 0:
                dedented_text = textwrap.dedent(edu_text).strip()
                edu_text = textwrap.fill(dedented_text, width=word_wrap)

            elements[elem_id]['text'] = edu_text
            ordered_edus.append(elem_id)

        else:  # elem_type == 'group':
            elements[elem_id]['group_type'] = elem.attrib.get('type')
    return children, elements, ordered_edus










