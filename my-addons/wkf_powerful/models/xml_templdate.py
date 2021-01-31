# -*- coding: utf-8 -*-
##############################################################################

bton_contain_template= """
    <div class="o_statusbar_buttons"></div>
"""

btn_template = """
    <button name="wkf_button_action" string="%(btn_str)s"
          context="{'trans_id':'%(trans_id)s'}"
          attrs="{'invisible':[('x_wkf_state','!=', '%(vis_state)s')]}"
          type="object"
          class="oe_highlight"/>
"""

btn_show_log_template =  """
    <button name="wkf_button_show_log"
          string="%(btn_str)s"
          type="object"
          groups="%(btn_grp)s"
          />
"""

btn_wkf_reset_template =  """
    <button name="wkf_button_reset"
          string="%(btn_str)s"
          type="object"
          groups="%(btn_grp)s"
          context="{'wkf_id': %(btn_ctx)s}"
          attrs="{'invisible':[('x_wkf_state','in', [%(no_reset_states)s])]}"
          />
"""


arch_template_header = """
    <xpath expr="//header" position="after"></xpath>
"""

arch_template_no_header = """
    <xpath expr="//form/*" position="before"></xpath>
"""

wkf_contain_template="""
    <div class='o_form_statusbar o_from_wkf_contain'></div>
"""

wfk_field_state_template = """
    <field name="%s" widget="statusbar" readonly="1"  statusbar_visible="%s"/>
"""
wfk_field_note_template = """
    <span class="oe_inline">Note:<field name="%s" class="oe_inline" string="sss"/></span>
"""