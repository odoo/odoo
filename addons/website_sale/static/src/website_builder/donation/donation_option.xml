<?xml version="1.0" encoding="UTF-8"?>
<templates xml:space="preserve">

<t t-name="website_sale.DonationOption">
    <BuilderRow label.translate="Display Options" preview="false">
        <BuilderCheckbox id="'display_options_opt'" action="'toggleDisplayOptions'" />
    </BuilderRow>
    <BuilderRow t-if="!this.isActiveItem('no_input_opt')"
                label.translate="Pre-filled Options" preview="false">
        <BuilderCheckbox id="'pre_filled_opt'" action="'togglePrefilledOptions'" />
    </BuilderRow>
    <t t-if="this.isActiveItem('no_input_opt') || this.isActiveItem('pre_filled_opt')">
        <t t-set="translatedDefaultDescription">Add a description here</t>
        <BuilderList
                action="'setPrefilledOptions'"
                addItemTitle.translate="Add"
                itemShape="{ value: 'number', description: 'text' }"
                default="{ value: '50', description: translatedDefaultDescription }"
                columnWidth="{ value: 'w-25' }"
                hiddenProperties="this.isActiveItem('pre_filled_descriptions_opt') ? [] : ['description']"
        />
        <BuilderRow label.translate="Descriptions" level="1" preview="false">
            <BuilderCheckbox id="'pre_filled_descriptions_opt'" action="'toggleDescriptions'" />
        </BuilderRow>
    </t>
    <BuilderRow label.translate="Custom Amount" preview="false">
        <BuilderSelect action="'selectAmountInput'">
            <t t-if="!this.isActiveItem('display_options_opt') || this.isActiveItem('pre_filled_opt') || this.isActiveItem('no_input_opt')">
                <BuilderSelectItem id="'free_amount_opt'" actionParam="'freeAmount'">Input</BuilderSelectItem>
            </t>
            <t t-if="this.isActiveItem('display_options_opt')">
                <BuilderSelectItem id="'slider_opt'" actionParam="'slider'">Slider</BuilderSelectItem>
            </t>
            <t t-if="this.isActiveItem('no_input_opt') || this.isActiveItem('pre_filled_opt')">
                <BuilderSelectItem id="'no_input_opt'" actionParam="''">None</BuilderSelectItem>
            </t>
        </BuilderSelect>
    </BuilderRow>
    <BuilderRow t-if="!this.isActiveItem('no_input_opt')"
                label.translate="Minimum" level="1">
        <BuilderNumberInput step="1" action="'setMinimumAmount'"/>
    </BuilderRow>
    <t t-if="this.isActiveItem('slider_opt')">
        <BuilderRow label.translate="Maximum" level="1">
            <BuilderNumberInput step="1" action="'setMaximumAmount'"/>
        </BuilderRow>
        <BuilderRow label.translate="Step" level="1">
            <BuilderNumberInput step="1" action="'setSliderStep'"/>
        </BuilderRow>
    </t>
    <BuilderRow label.translate="Default Amount">
        <BuilderNumberInput step="1" default="25" dataAttributeAction="'defaultAmount'"/>
    </BuilderRow>
</t>

<t t-inherit="website.BuilderOptions" t-inherit-mode="extension">
    <xpath expr="//t[@id='snippet_specific_options']" position="after">
        <donation_option selector=".s_donation"/>
    </xpath>
</t>

</templates>
