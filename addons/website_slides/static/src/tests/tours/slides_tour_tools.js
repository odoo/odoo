odoo.define('website_slides.tour.tools', function (require) {
'use strict';

/*
 * PUBLISHER / CONTENT CREATION
 */

var addTrainingCourse = function () {
	return [
	{
		content: 'eLearning: click on New (top-menu)',
		trigger: 'li.o_new_content_menu a'
	}, {
		content: 'eLearning: click on New Course',
		trigger: 'a:contains("New Course")'
	}, {
		content: 'eLearning: set name',
		trigger: 'input[name="name"]',
		run: 'text How to Déboulonnate',
	}, {
		content: 'eLearning: click on tags',
		trigger: 'ul.select2-choices:first',
	}, {
		content: 'eLearning: select gardener tag',
		trigger: 'div.select2-result-label:contains("Gardener")',
		in_modal: false,
	}, {
		content: 'eLearning: set description',
		trigger: 'textarea[name="description"]',
		run: 'text Déboulonnate is very common at Fleurus',
	}, {
		content: 'eLearning: we want reviews',
		trigger: 'input[name="allow_comment"]',
	}, {
		content: 'eLearning: seems cool, create it',
		trigger: 'button:contains("Create")',
	}, {
		content: 'eLearning: launch course edition',
		trigger: 'li[id="edit-page-menu"] a',
	}, {
		content: 'eLearning: double click image to edit it',
		trigger: 'img.o_wslides_course_pict',
		run: 'dblclick',
	}, {
		content: 'eLearning: click pâtissière',
		trigger: 'img[title="sell.jpg"]',
	}, {
		content: 'eLearning: validate pâtissière',
		trigger: 'footer.modal-footer button:contains("Add")',
	}, {
		content: 'eLearning: is the pâtissière set ?',
		trigger: 'img.o_wslides_course_pict',
		run: function () {
			if ($('img.o_wslides_course_pict').attr('src').endsWith('sell.jpg')) {
				$('img.o_wslides_course_pict').addClass('o_wslides_tour_success');
			}
		},
	}, {
		content: 'eLearning: the pâtissière is set !',
		trigger: 'img.o_wslides_course_pict.o_wslides_tour_success',
	}, {
		content: 'eLearning: save course edition',
		trigger: 'button[data-action="save"]',
	}];
};

var checkCourseMembership = function () {
	return [
		{
		content: 'eLearning: course create with current member',
		extra_trigger: 'body:not(.editor_enable)',  // wait for editor to close
		trigger: '.o_wslides_js_course_join:contains("You\'re enrolled")',
		run: function () {} // check membership
		}
	];
};

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

var addVideoAndCreateSectionOnTheFly = function () {
	return [
		{
			content: 'eLearning: Add slide and a section on the fly with the add content button located at the bottom',
			trigger: '.o_wslides_js_slide_upload:last()'
		}, {
			content: 'elearning: Click on video type',
			trigger: "a[data-slide-type='video']",
		}, {
			content: 'eLearning: Set slide video url',
			trigger: 'input[name="url"]',
			run: 'text https://www.youtube.com/watch?v=tzZkrn1zoAA',
		}, {
			content: 'eLearning: click on sections',
			trigger: '.select2-choice:first',
		}, {
			content: 'eLearning: Set on the fly section name',
			trigger: '#s2id_autogen2_search',
			run: 'text Russian Folklore',
			in_modal: false
		}, {
			content: 'eLearning: select Russian Folklore',
			trigger: 'div.select2-result-label:first',
			in_modal: false
		},{
			content: 'elearning: Publish the slide and section',
			trigger: 'button.o_w_slide_upload.o_w_slide_upload_published',
		},
	];
};

/***
 * Test if the add content button on the section created on the fly works properly
 */
var addVideoToSectionCreatedOnTheFly = function () {
	return [
		{
			content: 'eLearning: Add content with the add content button located on the second section',
			trigger: '.o_wslides_slide_list_category_header:last .o_wslides_js_slide_upload'
		}, {
			content: 'eLearning: Click on video type',
			trigger: "a[data-slide-type='video']",
		}, {
			content: 'eLearning: Set slide video url',
			trigger: 'input[name="url"]',
			run: 'text https://www.youtube.com/watch?v=7DljgSrTbNE',
		}, {
			content: 'eLearning: Create and publish the slide',
			trigger: 'button.o_w_slide_upload.o_w_slide_upload_published',
		},
	];
};

var addVideoWithNoSection = function () {
	return [
		{
			content: 'eLearning: Add uncategorized slide',
			trigger: '.o_wslides_js_slide_upload:last()'
		}, {
			content: 'elearning: Click on video type',
			trigger: "a[data-slide-type='video']",
		}, {
			content: 'eLearning: Set slide video url',
			trigger: 'input[name="url"]',
			run: 'text https://www.youtube.com/watch?v=SYnVYJDxu2Q',
		},{
			content: 'elearning: Publish the slide and section',
			trigger: 'button.o_w_slide_upload.o_w_slide_upload_published',
		},
	];
};

var dragAndDropSlide = function () {
	return [
		{
			content: 'eLearning: move slide from section to section',
			trigger: ".o_wslides_slide_list_category_header:last>.o_wslides_slides_list_drag",
			run: "drag_and_drop",
		}
	];
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
    content: 'eLearning: select Theory tag',
    trigger: 'div.select2-result-label:contains("Theory")',
    in_modal: false,
}, {
	content: 'eLearning: fill webpage completion time',
	trigger: 'input[name=duration]',
	run: 'text 4',
}];
};

var addExistingCourseTag = function () {
	return [
{
    content: 'eLearning: click on Add Tag',
    trigger: 'a.o_wslides_js_channel_tag_add',
}, {
    content: 'eLearning: click on tag dropdown',
    trigger: 'a.select2-choice:first',
}, {
    content: 'eLearning: select advanced tag',
    trigger: 'div.select2-result-label:contains("Advanced")',
    in_modal: false,
}, {
    content: 'eLearning: add existing course tag',
    trigger: 'footer.modal-footer button:contains("Add")'
}];
};

var addNewCourseTag = function (courseTagName) {
	return [
{
    content: 'eLearning: click on Add Tag',
    trigger: 'a.o_wslides_js_channel_tag_add',
}, {
    content: 'eLearning: click on tag dropdown',
	trigger: 'a.select2-choice:first',
}, {
    content: 'eLearning: add a new course tag',
	trigger: 'a.select2-choice:first',
	run: function () {
		// directly add new tag since we can assume select2 works correctly
		$('#tag_id').select2('data', {id:'123', text: courseTagName, create: true});
		$('#tag_id').trigger('change');
	}
}, {
    content: 'eLearning: click on tag group dropdown',
	trigger: 'a.select2-choice:last',
}, {
	content: 'eLearning: select Tags tag group',
    trigger: 'div.select2-result-label:contains("Tags")',
	in_modal: false,
}, {
    content: 'eLearning: add new course tag',
    trigger: 'footer.modal-footer button:contains("Add")'
}];
};
var publishNewlyAddedSlide = function () {
	return   [
{
	content: 'eLearning: publish newly added course',
	trigger: 'span:contains("Dschinghis Khan - Moskau 1979")',  // wait for slide to appear
	run: function () {
		$('span.o_wslides_js_slide_toggle_is_preview:last').click();
	}
}, {
	content: 'eLearning: Check that the publishing mechanism worked',
	trigger: '.badge-success',
	run: function (){}
}];
};

var archiveSlide = function (){
	return [
		{
			content: 'eLearning: Archive slide',
			trigger: '.o_wslides_js_slide_archive:last',
		},
		{
			content: 'eLearning: Confirm Archive',
			trigger: 'button:contains("Archive")'
		}
	];
};

var testSlideOrder = function (){
	return [
		{
			content: 'eLearning: Change the page to check if the ordering still holds up',
			trigger: '.o_wslides_js_slides_list_slide_link:first',
		},
		{
			content: 'eLearning:Go back to the course to check if the ordering still holds up',
			trigger: ".o_wslides_fs_sidebar_header a:contains('How to Déboulonnate')",
		},
		{
			content: 'eLearning: Test slide at first position',
			trigger: ".o_wslides_js_list_item:not('.o_not_editable'):first:contains('Boney M. - Rasputin')",
			run: function () {}
		},
		{
			content: 'eLearning: Test slide at last position',
			trigger: ".o_wslides_js_slides_list_slide_link:last:contains('RUSSIAN ROAD - w/ English Lyrics')",
			run: function () {}
		}
	];
};

return {
	addTrainingCourse: addTrainingCourse,
	checkCourseMembership: checkCourseMembership,
	addSection: addSection,
	addVideoToSection: addVideoToSection,
	addWebPageToSection: addWebPageToSection,
	addExistingCourseTag: addExistingCourseTag,
	addNewCourseTag: addNewCourseTag,
	addVideoAndCreateSectionOnTheFly: addVideoAndCreateSectionOnTheFly,
	addVideoToSectionCreatedOnTheFly: addVideoToSectionCreatedOnTheFly,
	addVideoWithNoSection: addVideoWithNoSection,
	dragAndDropSlide: dragAndDropSlide,
	publishNewlyAddedSlide: publishNewlyAddedSlide,
	archiveSlide: archiveSlide,
	testSlideOrder: testSlideOrder
};

});
