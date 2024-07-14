# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo.addons.mrp_workorder.tests.common import TestMrpWorkorderCommon
from odoo.tests import Form


class TestWorkorderClientActionCommon(TestMrpWorkorderCommon):
    @classmethod
    def _get_client_action_url(cls, workorder_id):
        action = cls.env["ir.actions.actions"]._for_xml_id("mrp_workorder.tablet_client_action")
        return '/web#action=%s&active_id=%s' % (action['id'], workorder_id)

    @classmethod
    def setUpClass(cls):
        super(TestWorkorderClientActionCommon, cls).setUpClass()
        cls.env.ref('base.user_admin').name = "Mitchell Admin"
        cls.picking_type_manufacturing = cls.env.ref('stock.warehouse0').manu_type_id
        cls.user_admin = cls.env.ref('base.user_admin')
        cls.potion = cls.env['product.product'].create({
            'name': 'Magic Potion',
            'type': 'product'})
        cls.ingredient_1 = cls.env['product.product'].create({
            'name': 'Magic',
            'type': 'consu'})
        cls.bom_potion = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.potion.product_tmpl_id.id,
            'consumption': 'flexible',
            'product_qty': 1.0,
            'bom_line_ids': [(0, 0, {'product_id': cls.ingredient_1.id, 'product_qty': 1})]})
        cls.wizard_op_1 = cls.env['mrp.routing.workcenter'].create({
            'name': 'Wizarding Operation',
            'workcenter_id': cls.workcenter_2.id,
            'bom_id': cls.bom_potion.id,
            'time_cycle': 12,
            'sequence': 1})
        cls.wizarding_step_1 = cls.env['quality.point'].create({
            'title': 'Gather Magic Step',
            'product_ids': [(4, cls.potion.id)],
            'picking_type_ids': [(4, cls.picking_type_manufacturing.id)],
            'operation_id': cls.wizard_op_1.id,
            'test_type_id': cls.env.ref('quality.test_type_instructions').id,
            'sequence': 1,
            'note': '<p>Close your eyes and concentrate</p>'})
        cls.step_image_html = '<p><img src="/stock/static/description/icon.png"></p>'
        cls.wizarding_step_2 = cls.env['quality.point'].create({
            'title': 'Cast Magic Step',
            'product_ids': [(4, cls.potion.id)],
            'picking_type_ids': [(4, cls.picking_type_manufacturing.id)],
            'operation_id': cls.wizard_op_1.id,
            'test_type_id': cls.env.ref('quality.test_type_instructions').id,
            'sequence': 2,
            'note': '<p>Wave your hands in the air like you just do not care! %s</p>' % cls.step_image_html})


# IMPORTANT: These tests need to be at_install because expected behavior is different when plm is installed
# Also, since tours are ONLY allowed in the post_install case, we do a pure python recreation of the flow
# here and only run tours in the corresponding plm module
class TestPickingWorkorderClientActionSuggestImprovement(TestWorkorderClientActionCommon):
    def test_add_step(self):
        """ Add 2 new steps as instruction in the tablet view via the 'suggest
        worksheet improvement' and check that BoM chatter messages are correct:
         - One with title + instructions,
         - One with NO title or instructions (i.e. check no 'False' values displayed) """
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.potion
        mo = mo_form.save()
        mo.action_confirm()
        self.assertEqual(len(mo.workorder_ids.check_ids), 2)
        wo = mo.workorder_ids[0]
        wo.button_start()

        new_step_title = "New Magical Step"
        new_step_note = "Do extra magic"

        # add step with title + instructions
        action = wo.action_add_step()
        add_step_form = Form(self.env[action['res_model']].with_context(action['context']), view=action['views'][0][0])
        add_step_form.title = new_step_title
        add_step_form.note = new_step_note
        add_step = add_step_form.save()
        add_step.with_user(self.user_admin).add_check_in_chain()

        # add step with NO title or instructions
        action = wo.action_add_step()
        add_step_form = Form(self.env[action['res_model']].with_context(action['context']), view=action['views'][0][0])
        add_step = add_step_form.save()
        add_step.with_user(self.user_admin).add_check_in_chain()

        activities = mo.bom_id.activity_ids
        self.assertEqual(len(activities), 2, 'should be 2 activities created on the BoM')
        activity = activities[0]
        self.assertEqual(activity.summary, 'BoM feedback %s (%s)' % (new_step_title, mo.name))
        self.assertEqual(activity.note, Markup('<b>New Step suggested by Mitchell Admin</b><br><b>Instruction:</b><p>%s</p>' % new_step_note))
        activity = activities[1]
        self.assertEqual(activity.summary, 'BoM feedback %s (%s)' % (add_step.test_type, mo.name), "Title of step should have defaulted to its test_type")
        self.assertEqual(activity.note, Markup('<b>New Step suggested by Mitchell Admin</b>'))

    def test_remove_step(self):
        """ Removes steps in the tablet view via the 'suggest
        worksheet improvement' and check that BoM chatter message is correct:
        - Existing BoM step with a comment (for why step should be removed),
        - Existing BoM step without a comment, i.e. check no 'False' values displayed
        - An added step (via 'suggest worksheet improvement'), i.e. check NO activity created about its removal
        """
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.potion
        mo = mo_form.save()
        mo.action_confirm()
        self.assertEqual(len(mo.workorder_ids.check_ids), 2)
        wo = mo.workorder_ids[0]
        wo.button_start()

        remove_step_comment = "The magic is already within me"
        new_step_title = "Temporary Magical Step"

        # remove existing BoM step with a comment
        action = wo.action_propose_change('remove_step', wo.check_ids[0].id)
        remove_step_form = Form(self.env[action['res_model']].with_context(action['context']), view=action['views'][0][0])
        remove_step_form.comment = remove_step_comment
        remove_step = remove_step_form.save()
        remove_step.with_user(self.user_admin).process()

        # add a temporary new step (via suggestion) => remove it
        action = wo.action_add_step()
        add_step_form = Form(self.env[action['res_model']].with_context(action['context']), view=action['views'][0][0])
        add_step_form.title = new_step_title
        add_step = add_step_form.save()
        add_step.with_user(self.user_admin).add_check_in_chain()
        wo.current_quality_check_id = add_step

        # remove existing BoM step without a comment
        wo.current_quality_check_id = wo.check_ids[1]
        action = wo.action_propose_change('remove_step', wo.check_ids[1].id)
        remove_step_form = Form(self.env[action['res_model']].with_context(action['context']), view=action['views'][0][0])
        remove_step = remove_step_form.save()
        remove_step.with_user(self.user_admin).process()

        activities = mo.bom_id.activity_ids
        self.assertEqual(len(activities), 3, 'should be 3 activities created on the BoM')
        activity = activities[0]
        self.assertEqual(activity.summary, 'BoM feedback %s (%s)' % (wo.check_ids[0].title, mo.name))
        self.assertEqual(activity.note, Markup('<span><b>Mitchell Admin suggests to delete this instruction</b><br><b>Reason:</b> %s</span>' % remove_step_comment))
        activity = activities[1]
        self.assertEqual(activity.summary, 'BoM feedback %s (%s)' % (new_step_title, mo.name))
        self.assertEqual(activity.note, Markup('<b>New Step suggested by Mitchell Admin</b>'))
        # !! expected behavior: there is NO chatter message about the new step being removed !!
        activity = activities[2]
        self.assertEqual(activity.summary, 'BoM feedback %s (%s)' % (wo.check_ids[1].title, mo.name))
        self.assertEqual(activity.note, Markup('<b>Mitchell Admin suggests to delete this instruction</b>'))

    def test_update_instructions(self):
        """ 'Update Instructions' for a step in the tablet view via the 'suggest
        worksheet improvement' and check that the BoM chatter messages are correct:
        - Existing BoM step with no title provided (i.e. keep original title) + no note + no comment, i.e. check no 'False' values displayed
        - Existing BoM step with a title + note + comment
        - An added step (via 'suggest worksheet improvement'), i.e. check activity is created for its update"""
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.potion
        mo = mo_form.save()
        mo.action_confirm()
        self.assertEqual(len(mo.workorder_ids.check_ids), 2)
        wo = mo.workorder_ids[0]
        wo.button_start()

        original_title = wo.current_quality_check_id.title
        updated_title = "Pre-magic Step"
        updated_note = "This is the step before magic is done"
        update_comment = "This step was inaccurate"
        new_step_title = "Extra Magical Step"
        new_step_note = "Make it extra magical"

        # update existing BoM step with NO title + NO instruction + NO comment
        action = wo.action_propose_change('update_step', wo.check_ids[0].id)
        update_step_form = Form(self.env[action['res_model']].with_context(action['context']), view=action['views'][0][0])
        update_step_form.title = ""
        update_step = update_step_form.save()
        update_step.with_user(self.user_admin).process()
        self.assertEqual(wo.current_quality_check_id.title, original_title, "When no title provided, keep original title")

        # update existing BoM step with title + instruction + comment
        action = wo.action_propose_change('update_step', wo.check_ids[0].id)
        update_step_form = Form(self.env[action['res_model']].with_context(action['context']), view=action['views'][0][0])
        update_step_form.title = updated_title
        update_step_form.note = updated_note
        update_step_form.comment = update_comment
        update_step = update_step_form.save()
        update_step.with_user(self.user_admin).process()
        self.assertEqual(wo.current_quality_check_id.title, updated_title, "Title didn't correctly update")
        self.assertEqual(wo.current_quality_check_id.note, Markup("<p>%s</p>" % updated_note), "Instruction didn't correctly update")

        # add a new step (via suggestion) => update it
        action = wo.action_add_step()
        add_step_form = Form(self.env[action['res_model']].with_context(action['context']), view=action['views'][0][0])
        add_step_form.title = new_step_title
        add_step = add_step_form.save()
        add_step.with_user(self.user_admin).add_check_in_chain()
        wo.current_quality_check_id = add_step
        action = wo.action_propose_change('update_step', add_step.id)
        update_step_form = Form(self.env[action['res_model']].with_context(action['context']), view=action['views'][0][0])
        update_step_form.title = ""
        update_step_form.note = new_step_note
        update_step = update_step_form.save()
        update_step.with_user(self.user_admin).process()
        self.assertEqual(add_step.note, Markup("<p>%s</p>" % new_step_note), "New step's note should have been updated")

        activities = mo.bom_id.activity_ids
        self.assertEqual(len(activities), 4, 'should be 4 activities created on the BoM')
        # existing BoM step
        activity = activities[0]
        self.assertEqual(activity.summary, 'BoM feedback %s (%s)' % (original_title, mo.name))
        self.assertEqual(activity.note, Markup('<b>New Instruction suggested by Mitchell Admin</b>'))
        activity = activities[1]
        self.assertEqual(activity.summary, 'BoM feedback %s (%s)' % (original_title, mo.name))
        self.assertEqual(activity.note, Markup('<b>New Instruction suggested by Mitchell Admin</b><br><p>%s</p><br><b>Reason:</b> %s<br><b>New Title suggested: %s</b>') % (updated_note, update_comment, updated_title))
        # suggested new step
        activity = activities[2]
        self.assertEqual(activity.summary, 'BoM feedback %s (%s)' % (new_step_title, mo.name))
        self.assertEqual(activity.note, Markup('<b>New Step suggested by Mitchell Admin</b>'))
        activity = activities[3]
        self.assertEqual(activity.summary, 'BoM feedback %s (%s)' % (new_step_title, mo.name))
        self.assertEqual(activity.note, Markup('<b>New Instruction suggested by Mitchell Admin</b><br><p>%s</p>') % new_step_note)

    def test_update_instructions_w_images(self):
        """ 'Update Instructions' for a step in the tablet view via the 'suggest
        worksheet improvement' when images are involved and check that the BoM chatter messages are correct:
        - Step with no image + update with an new_image => instruction should be: completely overwritten (only new_image)
        - Step with image and text + update only with 'new_text' => instruction should be: 'new_text' + image
        - Step with image + update with new_image + 'new_text' => instruction should be: new_image + 'new_text' """

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.potion
        mo = mo_form.save()
        mo.action_confirm()
        self.assertEqual(len(mo.workorder_ids.check_ids), 2)
        wo = mo.workorder_ids[0]
        wo.button_start()

        image = Markup(self.step_image_html)
        updated_note = "Improved magic instructions"
        updated_image = Markup('<p><img src="/mrp/static/description/icon.png"></p>')

        # update existing BoM step containing only text instructions with only an image
        action = wo.action_propose_change('update_step', wo.check_ids[0].id)
        update_step_form = Form(self.env[action['res_model']].with_context(action['context']), view=action['views'][0][0])
        update_step_form.note = image
        update_step = update_step_form.save()
        update_step.with_user(self.user_admin).process()
        self.assertEqual(wo.current_quality_check_id.note, image, "Step's note should have been updated to only be the new instruction image")

        # update existing BoM step containing text + image instructions with only text
        wo.current_quality_check_id = wo.check_ids[1]
        action = wo.action_propose_change('update_step', wo.check_ids[1].id)
        update_step_form = Form(self.env[action['res_model']].with_context(action['context']), view=action['views'][0][0])
        update_step_form.note = updated_note
        update_step = update_step_form.save()
        update_step.with_user(self.user_admin).process()
        self.assertEqual(wo.current_quality_check_id.note, Markup("<p>%s</p>" % updated_note) + image, "Step's note should have been updated to updated text + original image")

        # update existing BoM step containing text + image instructions with image + text
        action = wo.action_propose_change('update_step', wo.check_ids[1].id)
        update_step_form = Form(self.env[action['res_model']].with_context(action['context']), view=action['views'][0][0])
        update_step_form.note = updated_image + Markup("<p>%s</p>" % updated_note)
        update_step = update_step_form.save()
        update_step.with_user(self.user_admin).process()
        self.assertEqual(wo.current_quality_check_id.note, updated_image + Markup("<p>%s</p>" % updated_note), "Step's note should have been updated to updated image + updated text")

        activities = mo.bom_id.activity_ids
        self.assertEqual(len(activities), 3, 'should be 3 activities created on the BoM')
        # existing BoM step
        activity = activities[0]
        self.assertEqual(activity.summary, 'BoM feedback %s (%s)' % (wo.check_ids[0].title, mo.name))
        self.assertEqual(activity.note, Markup('<b>New Instruction suggested by Mitchell Admin</b><br>') + image)
        activity = activities[1]
        self.assertEqual(activity.summary, 'BoM feedback %s (%s)' % (wo.check_ids[1].title, mo.name))
        self.assertEqual(activity.note, Markup('<b>New Instruction suggested by Mitchell Admin</b><br><p>%s</p>' % updated_note), "Only the updated text instructions should be in chatter message to avoid wasting db space with unnecessary images")
        # suggested new step
        activity = activities[2]
        self.assertEqual(activity.summary, 'BoM feedback %s (%s)' % (wo.check_ids[1].title, mo.name))
        self.assertEqual(activity.note, Markup('<b>New Instruction suggested by Mitchell Admin</b><br>') + updated_image + Markup('<p>%s</p>' % updated_note))
