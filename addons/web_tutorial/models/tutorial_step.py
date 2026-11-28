from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.models import get_public_method
from odoo.tools import html2plaintext
from odoo.tools.translate import html_translate

GENERIC_BUTTONS = ('New', 'Edit', 'Delete', 'Duplicate', 'Archive', 'Unarchive')


class TutorialStep(models.Model):
    """ A step of a tutorial, done by the user or with Next, shown in the
    views of its action (or, without one, of its model) of its view types (of
    all types, if none, else among the ones of its action), with an HTML
    message; its ``name`` depending on its type (its element):

    - ``field``: a field of the form (e.g. ``partner_id``, or
      ``order_line.product_id`` for a field of the lines of a x2many field),
      done once focused; in a kanban view, a field of its quick create (or of
      the form, if opened without it);
    - ``method``: the method of the model called by a button of the view (e.g.
      ``action_post``), done once clicked;
    - ``server_action``: the xmlid of a server action bound to the model, done
      once run from the actions menu;
    - ``menu_item``: the xmlid of a menu of an app opening an action, done once
      clicked in the navbar;
    - ``generic_button``: a button of the web client (``New`` of a list or
      kanban view, ``Edit`` opening the form of a kanban quick create,
      ``Delete``, ``Duplicate``, ``Archive`` or ``Unarchive``), done once
      clicked;
    - ``dialog``: no element, its message being shown in a dialog in the
      middle of the screen (e.g. a welcome message), done with Next.

    A skippable step is only shown, the user going on with Next. The successive
    steps of the same model and views make a chapter of the tutorial, the ones
    without action joining the action of the chapter.
    """
    _name = 'web_tutorial.step'
    _description = "Tutorial Step"
    _order = "sequence, id"

    action_id = fields.Many2one("ir.actions.act_window", string="Action", index=True, ondelete="cascade")
    action_view_mode = fields.Char(related='action_id.view_mode')
    chapter = fields.Integer(
        compute='_compute_chapter',
        help="The successive steps of the same model and views make a chapter, the ones without action joining the "
             "action of the chapter",
    )
    message = fields.Html(required=True, translate=html_translate, help="What the user should do")
    model_id = fields.Many2one(
        "ir.model", string="Model", compute='_compute_model_id', store=True, readonly=False, precompute=True,
        required=True, index=True, ondelete="cascade",
    )
    name = fields.Char(
        copy=True,
        help="Depending on its type: the field (e.g. partner_id, or order_line.product_id for a field of the lines "
             "of a x2many field), the method of the model (e.g. action_post), the xmlid of a server action bound to "
             "the model, the xmlid of a menu, or the generic button (New, Edit, Delete, Duplicate, Archive or "
             "Unarchive); none for a dialog",
    )
    name_selection_options = fields.Json(
        compute='_compute_name_selection_options',
        help="The elements the step can name, as (value, label) pairs: the generic buttons, the server actions bound "
             "to its model or the menus of an app opening an action, depending on its type; none for the other types",
    )
    res_model = fields.Char(related='model_id.model', string="Model Name")
    sequence = fields.Integer(default=10)
    skippable = fields.Boolean()
    type = fields.Selection(
        [
            ('dialog', "Dialog"),
            ('field', "Field"),
            ('method', "Method"),
            ('server_action', "Server Action"),
            ('menu_item', "Menu Item"),
            ('generic_button', "Generic Button"),
        ],
        string="Element",
        required=True,
        help="The element of the step, pointed in the view; a dialog shows its message in the middle of the screen",
    )
    tutorial_id = fields.Many2one("web_tutorial.tutorial", required=True, index=True, ondelete="cascade")
    view_type_selection_options = fields.Json(
        compute='_compute_view_type_selection_options',
        help="The view types the step can be shown in, as (value, label) pairs: the ones of its action, all the ones "
             "of the window actions without action",
    )
    view_types = fields.Char(
        string="Views",
        help="The types of the views showing the step, separated by commas (e.g. list,kanban), among the ones of its "
             "action; all of them if empty",
    )

    @api.depends(
        'tutorial_id.step_ids.sequence', 'tutorial_id.step_ids.action_id', 'tutorial_id.step_ids.model_id',
        'tutorial_id.step_ids.view_types',
    )
    def _compute_chapter(self):
        """ Number the chapters of the tutorial as the client groups its steps """
        self.chapter = 0
        for tutorial in self.tutorial_id:
            chapter, views, action = 0, None, None
            for step in tutorial.step_ids.sorted('sequence'):
                step_views = (step.model_id, step._get_view_types())
                if step_views != views or (step.action_id and step.action_id != action):
                    chapter, views, action = chapter + 1, step_views, step.action_id
                if step in self:
                    step.chapter = chapter

    @api.depends('action_id')
    def _compute_model_id(self):
        for step in self.filtered('action_id'):
            step.model_id = self.env['ir.model']._get(step.action_id.sudo().res_model)

    @api.depends('type', 'model_id')
    def _compute_name_selection_options(self):
        for step in self:
            if step.type == 'generic_button':
                step.name_selection_options = [(button, button) for button in GENERIC_BUTTONS]
            elif step.type == 'server_action' and step.model_id:
                actions = self.env['ir.actions.server'].sudo().search([('binding_model_id', '=', step.model_id.id)])
                step.name_selection_options = self._get_xmlid_options(actions, 'name')
            elif step.type == 'menu_item':
                menus = self.env['ir.ui.menu'].sudo().search([('parent_id', '!=', False), ('action', '!=', False)])
                step.name_selection_options = self._get_xmlid_options(menus, 'complete_name')
            else:
                step.name_selection_options = []

    @api.depends('action_view_mode')
    def _compute_view_type_selection_options(self):
        selection = self.env['ir.actions.act_window.view']._fields['view_mode']._description_selection(self.env)
        for step in self:
            action_view_types = step._get_action_view_types()
            step.view_type_selection_options = [
                (view_type, label) for view_type, label in selection
                if not action_view_types or view_type in action_view_types
            ]

    @api.constrains('action_id', 'model_id')
    def _check_model(self):
        for step in self:
            if step.action_id and step.action_id.sudo().res_model != step.model_id.model:
                raise ValidationError(self.env._(
                    "The step “%(message)s” is in the views of %(model)s, not of the model of its action %(action)s.",
                    message=step._get_label(), model=step.model_id.model, action=step.action_id.name,
                ))

    @api.constrains('action_id', 'sequence', 'tutorial_id')
    def _check_starting_action(self):
        self.tutorial_id._check_starting_action()

    @api.constrains('view_types', 'action_id')
    def _check_view_types(self):
        all_view_types = self.env['ir.actions.act_window.view']._fields['view_mode'].get_values(self.env)
        for step in self:
            view_types = step.action_id and step._get_action_view_types() or all_view_types
            if invalid := [view_type for view_type in step._get_view_types() if view_type not in view_types]:
                raise ValidationError(self.env._(
                    "The step “%(message)s” is shown in %(invalid)s, which aren't among the view types it can be "
                    "shown in (%(view_types)s).",
                    message=step._get_label(), invalid=", ".join(invalid), view_types=", ".join(view_types),
                ))

    @api.constrains('type', 'name')
    def _check_type(self):
        for step in self:
            if step.type == 'dialog' and step.name:
                raise ValidationError(self.env._(
                    "The dialog step “%s” can't have a name, pointing at no element.", step._get_label(),
                ))
            if step.type != 'dialog' and not step.name:
                raise ValidationError(self.env._(
                    "The step “%s” needs the name of its element.", step._get_label(),
                ))

    @api.constrains('type', 'name', 'model_id')
    def _check_name(self):
        for step in self.filtered(lambda step: step.type != 'dialog' and step.name):
            model = self.env[step.model_id.model]
            if step.type == 'generic_button':
                step._check_generic_button()
            elif step.type == 'field':
                step._check_field(model)
            elif step.type == 'method':
                step._check_method(model)
            elif step.type == 'menu_item':
                step._check_menu_item()
            else:
                step._check_server_action(model)

    def _check_field(self, model):
        x2many, _dot, name = self.name.rpartition('.')
        field = model._fields.get(x2many or name)
        if x2many:
            field = field and field.type in ('one2many', 'many2many') and self.env[field.comodel_name]._fields.get(name)
        if not field:
            raise ValidationError(self.env._(
                "The field step “%(message)s” names %(field)s, which isn't a field of %(model)s, nor of the lines of "
                "one of its x2many fields.",
                message=self._get_label(), field=self.name, model=model._name,
            ))

    def _check_generic_button(self):
        if self.name not in GENERIC_BUTTONS:
            raise ValidationError(self.env._(
                "The step “%(message)s” names %(name)s, which isn't a generic button (%(buttons)s).",
                message=self._get_label(), name=self.name, buttons=", ".join(GENERIC_BUTTONS),
            ))

    def _check_menu_item(self):
        menu = self._get_record('ir.ui.menu')
        if not menu or not menu.sudo().parent_id or not menu.sudo().action:
            raise ValidationError(self.env._(
                "The step “%(message)s” opens %(menu)s, which isn't a menu of an app opening an action.",
                message=self._get_label(), menu=self.name,
            ))

    def _check_method(self, model):
        try:
            get_public_method(model, self.name)
        except (AccessError, AttributeError):
            raise ValidationError(self.env._(
                "The step “%(message)s” calls %(method)s, which isn't a public method of %(model)s.",
                message=self._get_label(), method=self.name, model=model._name,
            )) from None

    def _check_server_action(self, model):
        action = self._get_record('ir.actions.server')
        if not action or action.sudo().binding_model_id.model != model._name:
            raise ValidationError(self.env._(
                "The step “%(message)s” runs %(action)s, which isn't a server action bound to %(model)s.",
                message=self._get_label(), action=self.name, model=model._name,
            ))

    @api.onchange('action_id')
    def _onchange_action_id(self):
        """ Keep the view types of the new action only """
        if self.action_id:
            action_view_types = self._get_action_view_types()
            view_types = [view_type for view_type in self._get_view_types() if view_type in action_view_types]
            self.view_types = ",".join(view_types)

    @api.onchange('model_id')
    def _onchange_model_id(self):
        """ Clear the action of another model """
        if self.action_id and self.action_id.sudo().res_model != self.model_id.model:
            self.action_id = False

    @api.onchange('type')
    def _onchange_type(self):
        """ Clear the name of the former element """
        self.name = False

    def _get_action_view_types(self):
        """ Return the types of the views of the action of the step """
        self.ensure_one()
        return [view_type.strip() for view_type in (self.action_view_mode or "").split(',') if view_type.strip()]

    def _get_label(self):
        """ Return how the errors name the step: the text of its message """
        self.ensure_one()
        return html2plaintext(self.message or "") or self.name or ""

    def _get_menu_section(self):
        """ Return the xmlid of the section of the navbar opening the menu of
        the step: the menu itself if it's one, its ancestor otherwise; none if
        the menu was removed meanwhile (e.g. with its module), or moved to the
        top of the navbar """
        menu = self._get_record('ir.ui.menu')
        if not menu:
            return ""
        menu = menu.sudo()
        section_id = menu.parent_path.split('/')[1]
        if not section_id:
            return ""
        section = menu.browse(int(section_id))
        return section.get_external_id()[section.id]

    def _get_record(self, model):
        """ Return the record of the model the xmlid of the step names, if any """
        self.ensure_one()
        record = self.env.ref(self.name, raise_if_not_found=False) if '.' in self.name else None
        return record if record and record._name == model else None

    def _get_step_data(self):
        """ Return the step for the client, with the action, the model and the
        view types of its views, the name a server action has in its actions
        menu and the section of the navbar opening a menu """
        self.ensure_one()
        action = self.type == 'server_action' and self._get_record('ir.actions.server')
        return {
            'action_id': self.action_id.id,
            'action_name': action.sudo().name if action else "",
            'id': self.id,
            'menu_section': self._get_menu_section() if self.type == 'menu_item' else "",
            'message': str(self.message or ""),
            'name': self.name or "",
            'res_model': self.res_model,
            'skippable': self.skippable,
            'type': self.type,
            'view_types': self._get_view_types(),
        }

    def _get_view_types(self):
        """ Return the types of the views showing the step, empty for all of
        them """
        self.ensure_one()
        return [view_type.strip() for view_type in (self.view_types or "").split(',') if view_type.strip()]

    @api.model
    def _get_xmlid_options(self, records, label_field):
        """ Return the records having an xmlid as (xmlid, label) pairs, sorted
        by label """
        xmlids = records.get_external_id()
        return sorted(
            ((xmlids[record.id], record[label_field]) for record in records if xmlids[record.id]),
            key=lambda option: option[1],
        )
