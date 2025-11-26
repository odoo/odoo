<?xml version="1.0" encoding="UTF-8"?>
<templates xml:space="preserve">

<t t-name="website.FaqHorizontalOption">
    <BuilderRow label.translate="Topics">
        <BuilderButton
            type="'success'"
            action="'addItem'"
            actionParam="'.s_faq_horizontal_entry:last-of-type'"
            preview="false"
            applyTo="':scope > :has(.s_faq_horizontal_entry)'">
            Add Section
        </BuilderButton>
    </BuilderRow>
</t>

<t t-inherit="website.BuilderOptions" t-inherit-mode="extension">
    <xpath expr="//t[@id='snippet_specific_options']" position="after">
        <faq_horizontal_option template="website.FaqHorizontalOption" selector=".s_faq_horizontal"/>
    </xpath>
</t>

</templates>
