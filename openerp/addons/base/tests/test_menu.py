import openerp.tests.common as common

class test_menu(common.TransactionCase):

    def setUp(self):
        super(test_menu,self).setUp()
        self.Menus = self.registry('ir.ui.menu')

    def test_00_menu_deletion(self):
        """Verify that menu deletion works properly when there are child menus, and those
           are indeed made orphans"""
        cr, uid, Menus = self.cr, self.uid, self.Menus

        # Generic trick necessary for search() calls to avoid hidden menus 
        ctx = {'ir.ui.menu.full_list': True}

        root_id = Menus.create(cr, uid, {'name': 'Test root'})
        child1_id = Menus.create(cr, uid, {'name': 'Test child 1', 'parent_id': root_id})
        child2_id = Menus.create(cr, uid, {'name': 'Test child 2', 'parent_id': root_id})
        child21_id = Menus.create(cr, uid, {'name': 'Test child 2-1', 'parent_id': child2_id})

        all_ids = [root_id, child1_id, child2_id, child21_id]

        # delete and check that direct children are promoted to top-level
        # cfr. explanation in menu.unlink()
        Menus.unlink(cr, uid, [root_id])

        remaining_ids = Menus.search(cr, uid, [('id', 'in', all_ids)], order="id", context=ctx)
        self.assertEqual([child1_id, child2_id, child21_id], remaining_ids)

        orphan_ids =  Menus.search(cr, uid, [('id', 'in', all_ids), ('parent_id', '=', False)], order="id", context=ctx)
        self.assertEqual([child1_id, child2_id], orphan_ids)
