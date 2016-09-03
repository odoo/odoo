# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .rml2txt import parseString, parseNode


""" This engine is the minimalistic renderer of RML documents into text files,
    using spaces and newlines to format.

    It was needed in some special applications, where legal reports need to be
    printed in special (dot-matrix) printers.
"""
