/** @odoo-module **/

/*
 * PUBLISHER / CONTENT CREATION
 */

var addSection = function (sectionName, backend = false) {
	return [
{
    content: 'eLearning: click on Add Section',
    trigger: (backend ? 'iframe ' : '' ) + 'a.o_wslides_js_slide_section_add',
}, {
    content: 'eLearning: set section name',
    trigger: (backend ? 'iframe ' : '' ) + 'input[name="name"]',
    run: 'text ' + sectionName,
}, {
    content: 'eLearning: create section',
    trigger: (backend ? 'iframe ' : '' ) + 'footer.modal-footer button:contains("Save")'
}, {
	content: 'eLearning: section created empty',
	trigger: (backend ? 'iframe ' : '' ) + 'div.o_wslides_slide_list_category_header:contains("' + sectionName + '")',
}];
};

var addVideoToSection = function (sectionName, saveAsDraft, backend = false) {
	var base_steps = [
{
	content: 'eLearning: add content to section',
	trigger: (backend ? 'iframe ' : '' ) + 'div.o_wslides_slide_list_category_header:contains("' + sectionName + '") a:contains("Add Content")',
}, {
	content: 'eLearning: click on video',
	trigger: (backend ? 'iframe ' : '' ) + 'a[data-slide-category=video]',
}, {
	content: 'eLearning: fill video link',
	trigger: (backend ? 'iframe ' : '' ) + 'input[name=video_url]',
	run: 'text https://www.youtube.com/watch?v=pzmI3vAIhbE',
}, {
    content: 'eLearning: click outside to trigger onchange',
    trigger: (backend ? 'iframe ' : '' ) + 'div.o_w_slide_upload_modal_container',
    run: ({ tip_widget }) => {
		tip_widget.$anchor[0].click();
	},
}];
	if (saveAsDraft) {
		base_steps = [].concat(base_steps, [{
    content: 'eLearning: save as draft slide',
    extra_trigger: (backend ? 'iframe ' : '' ) + 'div.o_slide_preview img:not([src="/website_slides/static/src/img/document.png"])',  // wait for onchange to perform its duty
    trigger: (backend ? 'iframe ' : '' ) + 'footer.modal-footer button:contains("Save as Draft")',
}]);
	}
	else {
		base_steps = [].concat(base_steps, [{
    content: 'eLearning: create and publish slide',
    extra_trigger: (backend ? 'iframe ' : '' ) + 'div.o_slide_preview img:not([src="/website_slides/static/src/img/document.png"])',  // wait for onchange to perform its duty
    trigger: (backend ? 'iframe ' : '' ) + 'footer.modal-footer button:contains("Publish")',
}]);
	}
	return base_steps;
};

var addArticleToSection = function (sectionName, pageName, backend) {
	return [
{
	content: 'eLearning: add content to section',
	trigger: (backend ? 'iframe ' : '' ) + 'div.o_wslides_slide_list_category_header:contains("' + sectionName + '") a:contains("Add Content")',
}, {
	content: 'eLearning: click on article',
	trigger: (backend ? 'iframe ' : '' ) + 'a[data-slide-category=article]',
}, {
	content: 'eLearning: fill article title',
	trigger: (backend ? 'iframe ' : '' ) + 'input[name=name]',
	run: 'text ' + pageName,
}, {
    content: 'eLearning: click on tags',
    trigger: (backend ? 'iframe ' : '' ) + 'ul.select2-choices:first',
}, {
    content: 'eLearning: select Theory tag',
    trigger: (backend ? 'iframe ' : '' ) + 'div.select2-result-label:contains("Theory")',
    in_modal: false,
}, {
	content: 'eLearning: fill article completion time',
	trigger: (backend ? 'iframe ' : '' ) + 'input[name=duration]',
	run: 'text 4',
}, {
    content: 'eLearning: create and publish slide',
    trigger: (backend ? 'iframe ' : '' ) + 'footer.modal-footer button:contains("Publish")',
}];
};

var addExistingCourseTag = function (backend = false) {
	return [
{
    content: 'eLearning: click on Add Tag',
    trigger: (backend ? 'iframe ' : '' ) + 'a.o_wslides_js_channel_tag_add',
}, {
    content: 'eLearning: click on tag dropdown',
    trigger: (backend ? 'iframe ' : '' ) + 'a.select2-choice:first',
}, {
    content: 'eLearning: select advanced tag',
    trigger: (backend ? 'iframe ' : '' ) + 'div.select2-result-label:contains("Advanced")',
    in_modal: false,
}, {
    content: 'eLearning: add existing course tag',
    trigger: (backend ? 'iframe ' : '' ) + 'footer.modal-footer button:contains("Add")'
}, {
	content: 'eLearning: check that modal is closed',
	trigger: (backend ? 'iframe ' : '' ) + 'body:not(.modal-open)',
}];
};

var addNewCourseTag = function (courseTagName, backend) {
	return [
{
    content: 'eLearning: click on Add Tag',
    trigger: (backend ? 'iframe ' : '' ) + 'a.o_wslides_js_channel_tag_add',
}, {
    content: 'eLearning: click on tag dropdown',
	trigger: (backend ? 'iframe ' : '' ) + 'a.select2-choice:first',
}, {
    content: 'eLearning: add a new course tag',
	trigger: (backend ? 'iframe ' : '' ) + 'a.select2-choice:first',
	run: function () {
		// directly add new tag since we can assume select2 works correctly
		let $jq = $;
		if (backend) {
			$jq = $('.o_website_preview iframe:not(.o_ignore_in_tour)').contents()[0].defaultView.$;
		}
		$jq('#tag_id').select2('data', {id:'123', text: courseTagName, create: true});
		$jq('#tag_id').trigger('change');
	}
}, {
    content: 'eLearning: click on tag group dropdown',
	trigger: (backend ? 'iframe ' : '' ) + 'a.select2-choice:last',
}, {
	content: 'eLearning: select Tags tag group',
    trigger: (backend ? 'iframe ' : '' ) + 'div.select2-result-label:contains("Tags")',
	in_modal: false,
}, {
    content: 'eLearning: add new course tag',
    trigger: (backend ? 'iframe ' : '' ) + 'footer.modal-footer button:contains("Add")'
}, {
	content: 'eLearning: check that modal is closed',
	trigger: (backend ? 'iframe ' : '' ) + 'body:not(.modal-open)',
}];
};

export default {
	addSection: addSection,
	addVideoToSection: addVideoToSection,
	addArticleToSection: addArticleToSection,
	addExistingCourseTag: addExistingCourseTag,
	addNewCourseTag: addNewCourseTag,
};
