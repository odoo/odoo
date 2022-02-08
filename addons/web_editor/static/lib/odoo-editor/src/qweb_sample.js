export const qwebSample = /* xml */ `
<h1>Qweb examples</h1>
<div>
    <t t-set="foo1" t-value="2 + 1"></t>
    <t t-esc="object">foo</t>
    <t t-raw="object">foo_raw</t>
    <t t-esc="invisible"></t>
</div>

<h2>t-esc in link</h2>
<a href="#"="foo">Link without t-esc</a>
<a href="#" t-esc="foo">Link with t-esc</a>
<a href="#"><strong t-esc="foo">Link with t-esc and strong</strong></a>

<h2>if else part 1</h2>
<div>
        <t t-if="record.partner_id.parent_id">
            <t t-esc="record.partner_id.name">Brandon Freeman</t> (<t t-esc="record.partner_id.parent_id.name">Azure Interior</t>),
        </t>
        <t t-else="">
            <t t-esc="record.partner_id.name">Brandon Freeman</t>,
        </t>
</div>

<h2>if else part 2</h2>
<div>
    <t t-if="condition">
        <p>if1</p>
        <t t-if="condition">
            <p>if1.a</p>
        </t>
        <t t-elif="condition">
            <p>elif1.b</p>
        </t>
        <t t-else="condition">
            <p>elif1.c</p>
        </t>
    </t>
    <t t-if="condition">
        <p>if2</p>
    </t>
    <t t-elif="condition">
        <p>elif2.1</p>
    </t>
    <t t-else="condition">
        <p>elif2.1</p>

        <t t-if="condition">
            <p>if2.1.1</p>
        </t>
        <t t-elif="condition">
            <p>elif2.1.2</p>
        </t>
        <t t-else="condition">
            <p>elif2.1.3</p>
        </t>
    </t>
</div>

<h2>if else part 3</h2>
<div>
    <t t-if="condition">
        <p>if</p>
        <t t-if="condition">
            <p>if/if</p>
        </t>
        <t t-elif="condition">
            <p>if/elsif</p>
        </t>
        <t t-else="condition">
            <p>if/else</p>
        </t>
    </t>
    <t t-elif="condition">
        <p>elif</p>
        <t t-if="condition">
            <p>elif/if</p>
        </t>
        <t t-elif="condition">
            <p>elif/elif</p>
        </t>
        <t t-else="condition">
            <p>elif/else</p>
        </t>
    </t>
    <t t-else="condition">
        <p>else</p>
        <t t-if="condition">
            <p>else/if</p>
        </t>
        <t t-elif="condition">
            <p>else/elif</p>
        </t>
        <t t-else="condition">
            <p>else/else</p>
        </t>
    </t>
</div>

<div>
    <p t-esc="value">the value</p>
</div>

<div>
    <p t-if="condition">ok</p>
</div>
<div>
    <p t-if="user.birthday == today()">Happy birthday!</p>
    <p t-elif="user.login == 'root'">Welcome master!</p>
    <p t-else="">Welcome!</p>
</div>

<t t-foreach="[1, 2, 3]" t-as="i">
    <p><t t-esc="i"></t></p>
</t>

<p t-foreach="[1, 2, 3]" t-as="i">
    <t t-esc="i"></t>
</p>

<t t-set="foo2">
    <li>ok</li>
</t>
<t t-esc="foo2"></t>

<t t-call="other-template"></t>

<t t-call="other-template">
    <t t-set="foo3" t-value="1"></t>
</t>

<div>
    This template was called with content:
    <t t-raw="0"></t>
</div>

<h2>t-if should be inline</h2>
<div style="text-align: center; margin: 16px 0px 16px 0px;">
    <t t-if="not is_online or object.state != 'accepted'">
        <a t-attf-href="/calendar/meeting/accept?token={{object.access_token}}&amp;id={{object.event_id.id}}" style="padding: 5px 10px; color: #FFFFFF; text-decoration: none; background-color: #875A7B; border: 1px solid #875A7B; border-radius: 3px">
            Accept</a>
        <a t-attf-href="/calendar/meeting/decline?token={{object.access_token}}&amp;id={{object.event_id.id}}" style="padding: 5px 10px; color: #FFFFFF; text-decoration: none; background-color: #875A7B; border: 1px solid #875A7B; border-radius: 3px">
            Decline</a>
    </t>
    <a t-attf-href="/calendar/meeting/view?token={{object.access_token}}&amp;id={{object.event_id.id}}" style="padding: 5px 10px; color: #FFFFFF; text-decoration: none; background-color: #875A7B; border: 1px solid #875A7B; border-radius: 3px"><t t-esc="'Reschedule' if is_online and target_customer else 'View'">View</t></a>
</div>

<h2>should see the t-if background color</h2>
<div style="padding-top:5px;">
    <ul>
        <t t-if="not is_online and object.event_id.description">
            <li>Description: <t t-esc="object.event_id.description or ''" data-oe-t-inline="true">Meeting to discuss project plan and hash out the details of implementation.</t></li>
        </t>
        <t t-elif="is_online and object.event_id.description">
            <t t-set="object.event_id.description_to_html_lines()" t-value="splitted_description" data-oe-t-inline="true"></t>
            <li>Description:
                <ul t-foreach="splitted_description" t-as="description_line">
                    <li t-out="description_line or ''">Email: my.email@test.example.com</li>
                </ul>
            </li>
        </t>
    </ul>
</div>
`;
