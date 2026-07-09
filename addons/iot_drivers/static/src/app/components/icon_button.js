/* global owl */

const { Component, xml, props, types: t } = owl;

export class IconButton extends Component {
    props = props({
        onClick: t.function(),
        icon: t.string(),
        icon_class: t.string(),
    });

    static template = xml`
    <div class="d-flex align-items-center justify-content-center icon-button btn btn-primary" t-translation="off" t-on-click="this.props.onClick">
        <i class="oi" t-att-class="this.props.icon_class" t-att-data-icon="this.props.icon" aria-hidden="true"></i>
    </div>
  `;
}
