<?xml version="1.0" encoding="UTF-8"?>
<templates xml:space="preserve">

<t t-name="website.FontWeightPicker">
    <BuilderSelect action="'customizeWebsiteFontWeight'" actionParam="{ mainParam: this.props.variables }" disabled="this.props.disabled">
        <BuilderSelectItem actionValue="null">
            Auto
        </BuilderSelectItem>
        <t t-foreach="this.props.weights" t-as="weight" t-key="weight.value">
            <BuilderSelectItem actionValue="`${weight.value}`">
                <div class="d-flex justify-content-between align-items-center">
                    <span><t t-out="weight.label"/></span>
                    <span>(<t t-out="weight.value"/>)</span>
                </div>
            </BuilderSelectItem>
        </t>
    </BuilderSelect>
</t>

<t t-name="website.ThemeFontWeightOption">
    <BuilderRow
        label.translate="Font Weight"
        tooltip.translate="Controls the text's font weight. &quot;Auto&quot; inherits the parent value">
        <FontWeightPicker variables="this.props.regularVariables" weights="this.state.availableWeights"/>
        <t t-set-slot="collapse">
            <BuilderRow
                t-if="this.props.lightVariables"
                label.translate="Light"
                tooltip.translate="Weight for &quot;Light&quot; in the text toolbar. Unless Font Weight is &quot;Auto&quot;, only equal or lighter values are available."
                level="1">
                <FontWeightPicker variables="this.props.lightVariables" weights="this.filteredLightWeights"/>
            </BuilderRow>
            <BuilderRow
                t-if="this.props.boldVariables"
                label.translate="Bold"
                level="1"
                disabled="this.isBoldDisabled"
                tooltip="this.boldTooltip">
                <FontWeightPicker variables="this.props.boldVariables" weights="this.filteredBoldWeights" disabled="this.isBoldDisabled"/>
            </BuilderRow>
        </t>
    </BuilderRow>
</t>

</templates>
