<?xml version="1.0" encoding="UTF-8"?>
<templates xml:space="preserve">

<t t-name="website.BaseVisibilityOption">
    <BuilderRow label="this.props.label" tooltip="this.props.tooltip" t-if="!this.props.visibilityOpt or !this.isActiveItem(this.props.visibilityOpt)">
        <BuilderSelect action="this.props.visibilityAction">
            <BuilderSelectItem actionValue="'overTheContent'" id="'overTheContent'" t-if="this.hasPageOption(this.props.overlay)">Over The Content</BuilderSelectItem>
            <BuilderSelectItem actionValue="'regular'">Regular</BuilderSelectItem>
            <BuilderSelectItem actionValue="'hidden'">Hidden</BuilderSelectItem>
        </BuilderSelect>
    </BuilderRow>

    <t t-if="this.isActiveItem('overTheContent')">
        <BuilderRow label.translate="Background" level="this.props.level" t-if="this.props.bgColor and this.hasPageOption(this.props.bgColor)">
            <BuilderColorPicker action="'setPageWebsiteDirty'" styleAction="'background-color'" enabledTabs="['custom']"/>
        </BuilderRow>
        <BuilderRow label.translate="Text Color" level="this.props.level" t-if="this.props.textColor and this.hasPageOption(this.props.textColor)">
            <BuilderColorPicker action="'setPageWebsiteDirty'" styleAction="'color'" enabledTabs="['solid', 'custom']"/>
        </BuilderRow>
    </t>
</t>

</templates>
