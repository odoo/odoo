#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# test_recompute_oncascade
# ---------------------------------------------------------------------
# Copyright (c) 2017 Merchise Autrement [~º/~] and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the LICENCE attached (see LICENCE file) in the distribution
# package.
#
# Created on 2017-07-03


from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)


import random
from openerp.tests import common


class TestUnlink(common.TransactionCase):
    def setUp(self):
        super(TestUnlink, self).setUp()
        Parent = self.env['test_unlink.parent']
        self.Owner = self.env['test_unlink.owner']

        self.parent = parent = Parent.create({
            'name': 'The parent'
        })

        self.total = 0
        for value in range(1, 20):
            self.total += value
            self._create_child(name='Child %d' % value, value=value, parent=parent)

    def _create_child(self, name, value, parent):
        return self.Owner.create({
            'item_id': [CREATE_RELATED(
                name=name,
                value=value,
                parent_id=parent.id
            )]
        })

    def test_setup(self):
        'Our setup is sane.'
        self.assertEqual(self.total, self.parent.total)

    def test_cascade_works(self):
        'Deleting by cascade triggers recomputations.'
        owner = random.choice(self.Owner.search([]))
        parent = owner.item_id.parent_id
        total = parent.total
        value = owner.item_id.value
        items = len(parent.children_ids)

        # when we unlink the owner...
        owner.unlink()
        # the children will be delete by cascade
        self.assertEqual(items - 1, len(parent.children_ids))
        # we expect the parent to recompute the 'total'.
        self.assertEqual(total - value, parent.total)


def CREATE_RELATED(**values):
    return (0, 0, values)
