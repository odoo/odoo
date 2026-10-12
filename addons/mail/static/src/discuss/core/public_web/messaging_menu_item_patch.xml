<?xml version="1.0" encoding="UTF-8" ?>
<templates xml:space="preserve">

<t t-inherit="mail.MessagingMenuItem" t-inherit-mode="extension">
    <xpath expr="//t[@name='itemNameBefore']" position="inside">
        <i t-if="this.prependNameWithStar" class="oi oi-filled o-mail-favorite me-1" data-icon="star" t-att-title="this.starTitle" role="img"/>
    </xpath>
    <xpath expr="//t[@name='itemName']" position="replace">
        <div t-if="this.channel?.parent_channel_id" class="d-flex align-items-center">
            <span class="flex-shrink-0 opacity-75 small" t-att-title="this.channel.parent_channel_id.displayName" t-out="this.parentChannelShortName"/>
            <i class="oi o-xsmaller o-mx-0_5 flex-shrink-0 opacity-75" data-icon="chevron_forward"/>
            <span class="text-truncate" t-out="this.channel.thread.displayName"/>
        </div>
        <t t-else="">$0</t>
    </xpath>
    <xpath expr="//t[@name='itemName']" position="after">
        <span t-if="this.meetingStartText" class="o-mail-MessagingMenuItem-meetingStart flex-shrink-0 align-self-baseline fw-normal text-muted smaller ms-1">@ <t t-out="this.meetingStartText"/></span>
    </xpath>
    <xpath expr="//t[@t-set-slot='icon']" position="inside">
        <CountryFlag t-if="this.channel?.showCorrespondentCountry" country="this.channel.correspondentCountry" class="'o-mail-NotificationItem-country position-absolute border shadow-sm'"/>
    </xpath>
</t>
</templates>
