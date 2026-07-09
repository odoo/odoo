<?xml version="1.0" encoding="UTF-8"?>
<templates xml:space="preserve">

<t t-name="website.ClickableCardOption">
    <BuilderRow label.translate="Make it clickable" tooltip.translate="Make the entire card clickable. All inner links will not be accessible by the user.">
        <BuilderCheckbox id="'is_clickable_opt'" action="'setCardClickable'" preview="false"/>
    </BuilderRow>

    <t t-if="this.isActiveItem('is_clickable_opt')">
        <BuilderRow label.translate="Your URL" level="1">
            <BuilderUrlPicker action="'setCardAnchorUrl'" placeholder.translate="e.g. /page or URL" preview="false"/>
        </BuilderRow>

        <BuilderRow t-if="this.state.hasHref" label.translate="Open in New Tab" tooltip.translate="Enable this to open the link in a new browser tab" level="1">
            <BuilderCheckbox applyTo="'.stretched-link'" attributeAction="'target'" attributeActionValue="'_blank'" preview="false"/>
        </BuilderRow>
    </t>
</t>

<t t-inherit="website.BuilderOptions" t-inherit-mode="extension">
    <xpath expr="//animate_option" position="before">
        <clickable_card_option selector=".s_card" t-att-exclude="this.specialCardSelector + ', *:has(> .stretched-link) *'"/>
        <clickable_card_option t-att-selector="this.cardParentHandlers" exclude=".s_carousel_cards_item, *:has(> .stretched-link) *" applyTo=":scope > .s_card"/>
    </xpath>
</t>
</templates>
