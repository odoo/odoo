<?xml version="1.0" encoding="UTF-8" ?>
<templates xml:space="preserve">

    <t t-name="project.TaskCheckMark" t-inherit="web.BooleanField" t-inherit-mode="primary">
        <xpath expr="//CheckBox" position="replace">
            <a title="Mark as done"
               t-on-click.stop="this.onChange"
               t-attf-class="oi oi-lg oi-filled o_todo_done_button mx-0 px-1{{!this.isReached ? '-o' : ' done_button_enabled'}}" data-icon="check_circle"/>
        </xpath>
    </t>

</templates>
