import { renderToElement } from "@web/core/utils/render";
import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.websiteSlidesCoursePrerequisite = publicWidget.Widget.extend({
    selector: '.o_wslides_js_prerequisite_course',

    async start() {
        await this._super(...arguments);
        const channels = this.$el.data('channels');
        this.$el.popover({
            trigger: 'focus',
            placement: 'bottom',
            container: 'body',
            html: true,
            content: renderToElement('slide.course.prerequisite', {channels: channels}),
        });
    },
});

export default {
    websiteSlidesCoursePrerequisite: publicWidget.registry.websiteSlidesCoursePrerequisite
};
