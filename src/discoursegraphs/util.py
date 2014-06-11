#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Arne Neumann <discoursegraphs.programming@arne.cl>

"""
This module contains a number of helper functions.
"""

import os
import re

INTEGER_RE = re.compile('([0-9]+)')


def natural_sort_key(s):
    """
    returns a key that can be used in sort functions.

    Example:

    >>> items = ['A99', 'a1', 'a2', 'a10', 'a24', 'a12', 'a100']

    The normal sort function will ignore the natural order of the
    integers in the string:

    >>> print sorted(items)
    ['A99', 'a1', 'a10', 'a100', 'a12', 'a2', 'a24']

    When we use this function as a key to the sort function,
    the natural order of the integer is considered.

    >>> print sorted(items, key=natural_sort_key)
    ['A99', 'a1', 'a2', 'a10', 'a12', 'a24', 'a100']
    """
    return [int(text) if text.isdigit() else text
            for text in re.split(INTEGER_RE, s)]


def ensure_unicode(str_or_unicode):
    """
    tests, if the input is ``str`` or ``unicode``. if it is ``str``, it
    will be decoded from ``UTF-8`` to unicode.
    """
    if isinstance(str_or_unicode, str):
        return str_or_unicode.decode('utf-8')
    elif isinstance(str_or_unicode, unicode):
        return str_or_unicode
    else:
        raise ValueError("Input '{0}' should be a string or unicode, "
                         "but its of type {1}".format(str_or_unicode,
                                                      type(str_or_unicode)))


def ensure_utf8(str_or_unicode):
    """
    tests, if the input is ``str`` or ``unicode``. if it is ``unicode``,
    it will be encoded from ``unicode`` to ``utf-8``. otherwise, the
    input string is returned.
    """
    if isinstance(str_or_unicode, str):
        return str_or_unicode
    elif isinstance(str_or_unicode, unicode):
        return str_or_unicode.encode('utf-8')
    else:
        raise ValueError(
            "Input '{0}' should be a string or unicode, but it is of "
            "type {1}".format(str_or_unicode, type(str_or_unicode)))

def add_prefix(dict_like, prefix):
    """
    takes a dict (or dict-like object, e.g. etree._Attrib) and adds the
    given prefix to each key. Always returns a dict (via a typecast).

    Parameters
    ----------
    dict_like : dict (or similar)
        a dictionary or a container that implements .items()
    prefix : str
        the prefix string to be prepended to each key in the input dict

    Returns
    -------
    prefixed_dict : dict
        A dict, in which each key begins with the given prefix.
    """
    if not isinstance(dict_like, dict):
        try:
            dict_like = dict(dict_like)
        except Exception as e:
            raise ValueError("{0}\nCan't convert container to dict: "
                             "{1}".format(e, dict_like))
    return {prefix + k: v for (k, v) in dict_like.items()}


def create_dir(path):
    """
    Creates a directory. Warns, if the directory can't be accessed. Passes,
    if the directory already exists.

    @author: tzot (http://stackoverflow.com/a/600612)

    @param path: path to the directory to be created
    @type path: C{str}
    """
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST:
            pass
        elif exc.errno == errno.EACCES:
            print "Cannot create [%s]! Check Permissions" % path
        else:
            raise


def sanitize_string(string_or_unicode):
    """
    remove leading/trailing whitespace and always return unicode.
    """
    if isinstance(string_or_unicode, unicode):
        return string_or_unicode.strip()
    else:
        return string_or_unicode.decode('utf-8').strip()
