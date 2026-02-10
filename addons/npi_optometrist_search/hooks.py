# -*- coding: utf-8 -*-
"""Post-init hook: create External Provider views/action/menu after model is loaded."""

MODULE = 'npi_optometrist_search'


def post_init_hook(env):
    """Create External Provider UI so view validation does not run before model exists."""
    if env.ref('%s.view_external_provider_list' % MODULE, raise_if_not_found=False):
        return
    View = env['ir.ui.view']
    Data = env['ir.model.data']

    list_view = View.create({
        'name': 'external.provider.list',
        'model': 'external.provider',
        'arch': '''<list string="External Provider" create="1" edit="1" delete="1">
                <field name="name"/>
                <field name="phone"/>
                <field name="email"/>
                <field name="city"/>
                <field name="npi"/>
                <field name="company"/>
                <field name="license"/>
                <field name="taxonomy"/>
            </list>''',
    })
    Data.create({
        'name': 'view_external_provider_list',
        'module': MODULE,
        'model': 'ir.ui.view',
        'res_id': list_view.id,
        'noupdate': True,
    })

    form_view = View.create({
        'name': 'external.provider.form',
        'model': 'external.provider',
        'arch': '''<form string="External Provider">
                <sheet>
                    <group>
                        <group>
                            <field name="name"/>
                            <field name="phone"/>
                            <field name="email"/>
                            <field name="company"/>
                        </group>
                        <group>
                            <field name="npi"/>
                            <field name="license"/>
                            <field name="taxonomy"/>
                            <field name="city"/>
                            <field name="state"/>
                        </group>
                    </group>
                </sheet>
            </form>''',
    })
    Data.create({
        'name': 'view_external_provider_form',
        'module': MODULE,
        'model': 'ir.ui.view',
        'res_id': form_view.id,
        'noupdate': True,
    })

    action = env['ir.actions.act_window'].create({
        'name': 'External Provider',
        'res_model': 'external.provider',
        'view_mode': 'list,form',
    })
    Data.create({
        'name': 'action_external_provider',
        'module': MODULE,
        'model': 'ir.actions.act_window',
        'res_id': action.id,
        'noupdate': True,
    })

    root = env.ref('%s.menu_npi_optometrist_root' % MODULE, raise_if_not_found=False)
    if root:
        menu = env['ir.ui.menu'].create({
            'name': 'External Provider',
            'parent_id': root.id,
            'action': '%s,%d' % (action._name, action.id),
            'sequence': 20,
        })
        Data.create({
            'name': 'menu_external_provider',
            'module': MODULE,
            'model': 'ir.ui.menu',
            'res_id': menu.id,
            'noupdate': True,
        })
