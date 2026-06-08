import { Component, EventBus, xml } from '@odoo/owl';

export class AuthUI extends Component {
    static props = {
        bus: EventBus,
    }

    // Has to be in front of the block UI layer (which is z-index: 1070).
    static template = xml`
        <div
            id="three-ds-container"
            style="width: 500px;
            height: 600px;
            line-height: 200px;
            position: fixed;
            top: 25%;
            left: 40%;
            display: none;
            margin-top: -100px;
            margin-left: -150px;
            background-color: #ffffff;
            border-radius: 5px;mon
            text-align: center;
            z-index: 1072 !important;"
        >
            <iframe height="600" width="450" id="authorization-form" name="authorization-form"/>
        </div>
    `;
}
