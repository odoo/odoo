/** @odoo-module **/

import { contains } from "@web/../tests/utils";
import { getDataURLFromFile } from "@web/core/utils/urls";

/*
 * Constant
 */
const testPngImage = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAACXBIWXMAAC4jAAAuIwF4pT92AAAAD0lEQVQIHQEEAPv/AIdaewLIAV0IjhGPAAAAAElFTkSuQmCC';
const testPdf = 'JVBERi0xLjEKJWPDtsO2bW1lbnQKMSAwIG9iago8PC9UeXBlIC9DYXRhbG9nCi9QYWdlcyAyIDAgUgo+PgplbmRvYmoKMiAwIG9iago8PC9UeXBlIC9QYWdlcwovS2lkcyBbMyAwIFJdCi9Db3VudCAxCi9NZWRpYUJveCBbMCAwIDIxMCAyOTddCj4+CmVuZG9iagozIDAgb2JqCjw8L1R5cGUgL1BhZ2UKL1BhcmVudCAyIDAgUgovUmVzb3VyY2VzCjw8L0ZvbnQKPDwvRjEKPDwvVHlwZSAvRm9udAovU3VidHlwZSAvVHlwZTEKL0Jhc2VGb250IC9UaW1lcy1Sb21hbgo+Pgo+Pgo+PgovQ29udGVudHMgNCAwIFIKPj4KZW5kb2JqCjQgMCBvYmoKPDwvTGVuZ3RoIDQ4Pj4Kc3RyZWFtCkJUCi9GMSA0OCBUZgo1MCAxMzAgVGQKKFRFU1QpIFRqCkVUCmVuZHN0cmVhbQplbmRvYmoKeHJlZgowIDUKMDAwMDAwMDAwMCA2NTUzNSBmCjAwMDAwMDAwMjEgMDAwMDAgbgowMDAwMDAwMDY5IDAwMDAwIG4KMDAwMDAwMDE0OSAwMDAwMCBuCjAwMDAwMDAyOTggMDAwMDAgbgp0cmFpbGVyCjw8L1Jvb3QgMSAwIFIKL1NpemUgNQo+PgpzdGFydHhyZWYKMzgxCiUlRU9G';

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

const fillInFileInput = async (input, name, type, content) => {
    const blob = await (await fetch(`data:${type};base64,${content}`)).blob();
    const file = new File([blob], name, { type: type});
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(file);
    input.files = dataTransfer.files;
    input.dispatchEvent(new Event('change', { bubbles: true }));
};

const compareBase64Content = async (url, name, type, expectedContent) => {
    const blob = await (await fetch(url)).blob();
    const file = new File([blob], name, { type: type});
    const actualContent = await getDataURLFromFile(file).then(dataURL => dataURL.split(',', 2)[1]);
    return expectedContent === actualContent;
};

/**
 * Test the upload of an image file as a new content and especially the binary content of the uploaded image.
 */
const addImageToSection = (sectionName, pageName, backend) => {
    const prefix = backend ? 'iframe ' : '';
    return [
{
    content: 'eLearning: add content to section',
    trigger: `${prefix}div.o_wslides_slide_list_category_header:contains("${sectionName}") a:contains("Add Content")`,
}, {
    content: 'eLearning: click on image',
    trigger: `${prefix}a[data-slide-category=infographic]`,
}, {
    content: 'eLearning: choose upload from device',
    trigger: `${prefix}#source_type_local_file`,
}, {
    content: 'eLearning: load image',
    trigger: 'body',
    run: async () => {
        const uploadInput = backend ?
            document.getElementsByTagName('iframe')[0].contentWindow.document.getElementById('upload') :
            document.getElementById('upload');
        await fillInFileInput(uploadInput, 'Overview.png', 'image/png', testPngImage);
    },
}, {
    content: 'eLearning: ensure that the preview is displayed which means that data is loaded and can be submitted',
    trigger: `${prefix}#slide-image[src*="data:"]`,
}, {
    content: 'eLearning: create and publish slide',
    trigger: `${prefix}footer.modal-footer button:contains("Publish")`,
}, {
    content: 'eLearning: launch content',
    trigger: `${prefix}a.o_wslides_js_slides_list_slide_link:contains("Overview")`,
}, {
    content: 'eLearning: check uploaded image presence and perform comparison',
    trigger: (backend ? 'iframe ' : '') + '.o_wslides_fs_player img',
    run: async () => {
        const baseElement = backend ? document.querySelector('iframe').contentDocument : document;
        const img = baseElement.querySelector('.o_wslides_fs_player img');
        if (await compareBase64Content(img.getAttribute('src'), 'Overview.png', 'image/png', testPngImage)) {
            img.classList.add('o_wslides_tour_img_upload_success');
        }
    }
}, {
    content: 'eLearning: check uploaded image content',
    trigger: `${prefix}.o_wslides_fs_player img.o_wslides_tour_img_upload_success`,
},
{
    content: 'eLearning: back to course',
    trigger: `${prefix}.o_wslides_fs_sidebar_header a:contains("Déboulonnate")`,
},
{
    content: 'eLearning: check course page',
    trigger: `${prefix}.o_wslides_course_main`,
    isCheck: true,
}];
};

/**
 * Test the upload of a pdf file as a new content and especially the binary content of the uploaded pdf.
 */
const addPdfToSection = function (sectionName, pageName, backend) {
    const prefix = backend ? 'iframe ' : '';
    return [
{
    content: 'eLearning: add content to section',
    trigger: `${prefix}div.o_wslides_slide_list_category_header:contains("${sectionName}") a:contains("Add Content")`,
}, {
    content: 'eLearning: click on document',
    trigger: `${prefix}a[data-slide-category=document]`,
}, {
    content: 'eLearning: choose upload from device',
    trigger: `${prefix}#source_type_local_file`,
}, {
    content: 'eLearning: load pdf',
    trigger: 'body',
    run: async () => {
        const upload = backend ?
            document.getElementsByTagName('iframe')[0].contentWindow.document.getElementById('upload') :
            document.getElementById('upload');
        await fillInFileInput(upload, 'Exercise.pdf', 'application/pdf', testPdf);
    },
}, {
    content: 'eLearning: ensure that the preview is displayed which means that data is loaded and can be submitted',
    trigger: `${prefix}#slide-image[src*="data:"]`,
}, {
    content: 'eLearning: create and publish slide',
    trigger: `${prefix}footer.modal-footer button:contains("Publish")`,
}, {
    content: 'eLearning: launch content',
    trigger: `${prefix}a.o_wslides_js_slides_list_slide_link:contains("Exercise")`,
}, {
    content: 'eLearning: check uploaded pdf presence and perform comparison',
    trigger: (backend ? 'iframe.o_iframe ' : '') + '.o_wslides_fs_content',
    run: async () => {
        const baseElement = backend ? document.querySelector('iframe.o_iframe').contentDocument : document;
        await contains('iframe.o_wslides_iframe_viewer', { target: baseElement });
        const iframeViewerDoc = baseElement.querySelector('iframe.o_wslides_iframe_viewer').contentDocument;
        await contains('#PDFSlideViewer', { target: iframeViewerDoc });
        const pdfViewer = iframeViewerDoc.querySelector('#PDFSlideViewer');
        if (await compareBase64Content(pdfViewer.getAttribute('data-slideurl'), 'Exercise.pdf', 'application/pdf', testPdf)) {
            baseElement.querySelector('.o_wslides_fs_content').classList.add('o_wslides_tour_pdf_upload_success');
        }
    },
}, {
    content: 'eLearning: check uploaded pdf content',
    trigger: `${prefix}.o_wslides_fs_content.o_wslides_tour_pdf_upload_success`,
}, {
    content: 'eLearning: back to course',
    trigger: `${prefix}.o_wslides_fs_sidebar_header a:contains("Déboulonnate")`,
}, {
    content: 'eLearning: check course page',
    trigger: `${prefix}.o_wslides_course_main`,
    isCheck: true,
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
	addImageToSection: addImageToSection,
	addPdfToSection: addPdfToSection,
	addVideoToSection: addVideoToSection,
	addArticleToSection: addArticleToSection,
	addExistingCourseTag: addExistingCourseTag,
	addNewCourseTag: addNewCourseTag,
};
