/** @odoo-module */

import { ChatterContainer } from '../../components/chatter/chatter_container';
import { FormRenderer } from '@web/views/form/form_renderer';

export class ProjectSharingFormRenderer extends FormRenderer { }
ProjectSharingFormRenderer.components = {
    ...FormRenderer.components,
    ChatterContainer,
};
