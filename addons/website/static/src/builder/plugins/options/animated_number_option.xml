<?xml version="1.0" encoding="UTF-8"?>
<templates xml:space="preserve">

<t t-name="website.AnimatedNumberOption">
    <BuilderRow label.translate="Alignment">
       <BuilderButtonGroup applyTo="'.s_animated_number_content'">
            <BuilderButton ltrRtlMapping="'left-right'" classAction="'me-auto'" icon="'format_align_left'" title.translate="Left"/>
            <BuilderButton icon="'format_align_center'" title.translate="Center" classAction="'mx-auto'"/>
            <BuilderButton ltrRtlMapping="'left-right'" classAction="'ms-auto'" icon="'format_align_right'" title.translate="Right"/>
        </BuilderButtonGroup>
    </BuilderRow>
    <BuilderRow label.translate="Title Position">
        <BuilderButtonGroup applyTo="'.s_animated_number_content'">
            <BuilderButton
                applyTo="'.s_animated_number_label'"
                classAction="'d-none'"
                icon="'visibility_off'"
                title.translate="Hide"/>
            <BuilderButton
                classAction="'flex-column'"
                iconImg="'/website/static/src/img/snippets_options/pos_top.svg'"
                title.translate="Top"/>
            <BuilderButton
                ltrRtlMapping="'position-left-right'"
                classAction="'flex-row gap-2'"
                iconImg="'/website/static/src/img/snippets_options/pos_left.svg'"
                title.translate="Left"/>
            <BuilderButton
                ltrRtlMapping="'position-left-right'"
                classAction="'flex-row-reverse gap-2'"
                iconImg="'/website/static/src/img/snippets_options/pos_right.svg'"
                title.translate="Right"/>
            <BuilderButton
                classAction="'flex-column-reverse'"
                iconImg="'/website/static/src/img/snippets_options/pos_bottom.svg'"
                title.translate="Bottom"/>
        </BuilderButtonGroup>
    </BuilderRow>

    <BuilderContext preview="false">
        <BuilderRow label.translate="Start / End">
            <BuilderNumberInput title.translate="Start Value" dataAttributeAction="'startValue'" step="1" default="0"/>
            <BuilderNumberInput title.translate="End Value" dataAttributeAction="'endValue'" step="1" default="1000"/>
        </BuilderRow>
    </BuilderContext>
    <BuilderContext preview="false">
        <BuilderRow label.translate="Start After">
            <BuilderNumberInput styleAction="'animation-delay'" unit="'s'" default="0" min="0" step="0.1"/>
        </BuilderRow>
        <BuilderRow label.translate="Duration">
            <BuilderNumberInput styleAction="'animation-duration'" unit="'s'" default="1" min="0.1" step="0.1"/>
        </BuilderRow>
    </BuilderContext>
</t>

<t t-inherit="website.BuilderOptions" t-inherit-mode="extension">
    <xpath expr="//animate_option" position="before">
        <animated_number_option template="website.AnimatedNumberOption" selector=".s_animated_number"/>
    </xpath>
</t>


</templates>
