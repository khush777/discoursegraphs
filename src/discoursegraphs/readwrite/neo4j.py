#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Arne Neumann <discoursegraphs.programming@arne.cl>

"""
The ``neo4j`` module converts a ``DiscourseDocumentGraph`` into a ``Geoff``
string and/or exports it to a running ``Neo4j`` graph database.
"""

from neonx import write_to_neo, get_geoff
from discoursegraphs import DiscourseDocumentGraph
from discoursegraphs.util import ensure_utf8


def make_json_encodable(discoursegraph):
    """
    typecasts all `layers` sets to lists to make the graph
    convertible into `geoff` format.
    
    Parameters
    ----------
    discoursegraph : DiscourseDocumentGraph
    """
    for node_id in discoursegraph:
        discoursegraph.node[node_id]['layers'] = \
            list(discoursegraph.node[node_id]['layers'])
    for (from_id, to_id) in discoursegraph.edges_iter():
        # there might be multiple edges between 2 nodes
        edge_dict = discoursegraph.edge[from_id][to_id]
        for edge_id in edge_dict:
            edge_dict[edge_id]['layers'] = \
                list(edge_dict[edge_id]['layers'])

def add_node_ids_as_labels(discoursegraph):
    """
    Adds the ID of each node of a discourse graph as a label (an attribute
    named ``label`` with the value of the node ID) to itself. This will
    ignore nodes whose ID isn't a string or which already have a label
    attribute.

    Parameters
    ----------
    discoursegraph : DiscourseDocumentGraph
    """
    for node_id, properties in discoursegraph.nodes_iter(data=True):
        if not 'label' in properties and isinstance(node_id, (str, unicode)):
            discoursegraph.node[node_id]['label'] = ensure_utf8(node_id)


def convert_to_geoff(discoursegraph):
    """
    Parameters
    ----------
    discoursegraph : DiscourseDocumentGraph
        the discourse document graph to be converted into GEOFF format

    Returns
    -------
    geoff : string
        a geoff string representation of the discourse graph.
    """
    make_json_encodable(discoursegraph)
    add_node_ids_as_labels(discoursegraph)
    return get_geoff(discoursegraph, 'LINKS_TO')


def upload_to_neo4j(discoursegraph):
    """
    Parameters
    ----------
    discoursegraph : DiscourseDocumentGraph
        the discourse document graph to be uploaded to the local neo4j
        instance/

    Returns
    -------
    neonx_results : list of dict
        list of results from the `write_to_neo` function of neonx.
    """
    make_json_encodable(discoursegraph)
    add_node_ids_as_labels(discoursegraph)
    return write_to_neo("http://localhost:7474/db/data/",
        discoursegraph, edge_rel_name='LINKS_TO',
        edge_rel_attrib='edge_type', label_attrib='label')
