odoo.define('website_slides.tour.tools', function (require) {
'use strict';

/*
 * PUBLISHER / CONTENT CREATION
 */

var addSection = function (sectionName) {
	return [
{
    content: 'eLearning: click on Add Section',
    trigger: 'a.o_wslides_js_slide_section_add',
}, {
    content: 'eLearning: set section name',
    trigger: 'input[name="name"]',
    run: 'text ' + sectionName,
}, {
    content: 'eLearning: create section',
    trigger: 'footer.modal-footer button:contains("Save")'
}, {
	content: 'eLearning: section created empty',
	trigger: 'div.o_wslides_slide_list_category_header:contains("' + sectionName + '")',
}];
};

var addVideoToSection = function (sectionName, saveAsDraft) {
	var base_steps = [
{
	content: 'eLearning: add content to section',
	trigger: 'div.o_wslides_slide_list_category_header:contains("' + sectionName + '") a:contains("Add Content")',
}, {
	content: 'eLearning: click on video',
	trigger: 'a[data-slide-type=video]',
}, {
	content: 'eLearning: fill video link',
	trigger: 'input[name=url]',
	run: 'text https://www.youtube.com/watch?v=NvS351QKFV4&list=PLtVFNIekBzqIfO4u4n78i43etfw2n1St8&index=2&t=0s',
}, {
    content: 'eLearning: click outside to trigger onchange',
    trigger: 'div.o_w_slide_upload_modal_container',
    run: 'click',
}];
	if (saveAsDraft) {
		base_steps = [].concat(base_steps, [{
    content: 'eLearning: save as draft slide',
    extra_trigger: 'div.o_slide_preview img:not([src="/website_slides/static/src/img/document.png"])',  // wait for onchange to perform its duty
    trigger: 'footer.modal-footer button:contains("Save as Draft")',
}]);
	}
	else {
		base_steps = [].concat(base_steps, [{
    content: 'eLearning: create and publish slide',
    extra_trigger: 'div.o_slide_preview img:not([src="/website_slides/static/src/img/document.png"])',  // wait for onchange to perform its duty
    trigger: 'footer.modal-footer button:contains("Publish")',
}]);
	}
	return base_steps;
};

var addWebPageToSection = function (sectionName, pageName) {
	return [
{
	content: 'eLearning: add content to section',
	trigger: 'div.o_wslides_slide_list_category_header:contains("' + sectionName + '") a:contains("Add Content")',
}, {
	content: 'eLearning: click on webpage',
	trigger: 'a[data-slide-type=webpage]',
}, {
	content: 'eLearning: fill webpage title',
	trigger: 'input[name=name]',
	run: 'text ' + pageName,
}, {
    content: 'eLearning: click on tags',
    trigger: 'ul.select2-choices:first',
}, {
    content: 'eLearning: select gardener tag',
    trigger: 'div.select2-result-label:contains("Theory")',
    in_modal: false,
}, {
	content: 'eLearning: fill webpage completion time',
	trigger: 'input[name=duration]',
	run: 'text 4',
}];
};

return {
	addSection: addSection,
	addVideoToSection: addVideoToSection,
	addWebPageToSection: addWebPageToSection,
};

});
