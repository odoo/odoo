/** @odoo-module **/

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
    const prefix = backend ? ':iframe ' : '';
	return [
{
    content: 'eLearning: click on Add Section',
    trigger: prefix + 'a.o_wslides_js_slide_section_add',
    run: "click",
}, {
    content: 'eLearning: set section name',
    trigger: prefix + 'input[name="name"]',
    run: `edit ${sectionName}`,
}, {
    content: 'eLearning: create section',
    trigger: prefix + 'footer.modal-footer button:contains("Save")',
    run: "click",
}, {
	content: 'eLearning: section created empty',
	trigger: prefix + 'div.o_wslides_slide_list_category_header:contains("' + sectionName + '")',
    run: "click",
}];
};

const addContentToSection = (prefix, sectionName) => ({
    content: `eLearning: click on add content for section ${sectionName}`,
    trigger: `${prefix} div.o_wslides_slide_list_category_header:contains(${sectionName}) a:contains(Add Content)`,
    run: "click",
});

const clickOnAddTagDropdown = (prefix) => [
    {
        content: "Wait content is loaded before continue to avoid miss click",
        trigger: `${prefix} img[src*='boulonnate']`,
    },
    {
        content: "eLearning: click on Add Tag",
        trigger: `${prefix} a.o_wslides_js_channel_tag_add`,
        run: "click",
    },
    {
        content: "eLearning: click on tag dropdown",
        trigger: `${prefix} button.o_select_menu_toggler:first`,
        run: "click",
    },
];

var addVideoToSection = function (sectionName, saveAsDraft, backend = false) {
    const prefix = backend ? ':iframe ' : '';
	var base_steps = [
        addContentToSection(prefix, sectionName),
, {
	content: 'eLearning: click on video',
	trigger: prefix + 'a[data-slide-category=video]',
    run: "click",
}, {
	content: 'eLearning: fill video link',
	trigger: prefix + 'input[name=video_url]',
	run: "edit https://www.youtube.com/watch?v=pzmI3vAIhbE",
}, {
    content: 'eLearning: click outside to trigger onchange',
    trigger: prefix + 'div.o_w_slide_upload_modal_container',
    run: "click",
}];
    if (saveAsDraft) {
        base_steps = [].concat(base_steps, [
            {
                trigger:
                    prefix +
                    'div.o_slide_preview img:not([src="/website_slides/static/src/img/document.png"])', // wait for onchange to perform its duty
            },
            {
                content: "eLearning: save as draft slide",
                trigger: prefix + 'footer.modal-footer button:contains("Save as Draft")',
                run: "click",
            },
        ]);
    } else {
        base_steps = [].concat(base_steps, [
            {
                trigger:
                    prefix +
                    'div.o_slide_preview img:not([src="/website_slides/static/src/img/document.png"])', // wait for onchange to perform its duty
            },
            {
                content: "eLearning: create and publish slide",
                trigger: prefix + 'footer.modal-footer button:contains("Publish")',
                run: "click",
            },
        ]);
    }
    return base_steps;
};

var addArticleToSection = function (sectionName, pageName, backend) {
    const prefix = backend ? ':iframe ' : '';
	return [
        addContentToSection(prefix, sectionName),
        {
	content: 'eLearning: click on article',
	trigger: prefix + 'a[data-slide-category=article]',
    run: "click",
}, {
	content: 'eLearning: fill article title',
	trigger: prefix + 'input[name=name]',
	run: `edit ${pageName}`,
}, {
    content: 'eLearning: click on tags',
    trigger: prefix + 'button.o_select_menu_toggler:last',
    run: "click",
}, {
    content: 'eLearning: select Practice tag',
    trigger: prefix + 'div.o_select_menu_item_label:contains("Practice")',
    run: "click",
}, {
	content: 'eLearning: fill article completion time',
	trigger: prefix + 'input[name=duration]',
	run: "edit 4",
}, {
    content: 'eLearning: create and publish slide',
    trigger: prefix + 'footer.modal-footer button:contains("Publish")',
    run: "click",
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
    const prefix = backend ? ':iframe ' : '';
    return [
        addContentToSection(prefix, sectionName),
        {
    content: 'eLearning: click on image',
    trigger: `${prefix}a[data-slide-category=infographic]`,
    run: "click",
}, {
    content: 'eLearning: choose upload from device',
    trigger: `${prefix}#source_type_local_file`,
    run: "click",
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
    run: "click",
}, {
    content: 'eLearning: launch content',
    trigger: `${prefix} a.o_wslides_js_slides_list_slide_link:contains("Overview")[href$="?fullscreen=1"]`,
    run: "click",
},
{
    content: 'eLearning: check uploaded image presence and perform comparison',
    trigger: prefix + '.o_wslides_fs_player img',
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
    run: "click",
},
{
    content: 'eLearning: back to course',
    trigger: `${prefix}.o_wslides_fs_sidebar_header a:contains("Déboulonnate")`,
    run: "click",
},
{
    content: 'eLearning: check course page',
    trigger: `${prefix}.o_wslides_course_main`,
}];
};

/**
 * Test the upload of a pdf file as a new content and especially the binary content of the uploaded pdf.
 */
const addPdfToSection = function (sectionName, pageName, backend) {
    const prefix = backend ? ':iframe ' : '';
    return [
        addContentToSection(prefix, sectionName),
        {
    content: 'eLearning: click on document',
    trigger: `${prefix}a[data-slide-category=document]`,
    run: "click",
}, {
    content: 'eLearning: choose upload from device',
    trigger: `${prefix}#source_type_local_file`,
    run: "click",
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
    run: "click",
}, {
    content: 'eLearning: create and publish slide',
    trigger: `${prefix}footer.modal-footer button:contains("Publish")`,
    run: "click",
}, {
    content: 'eLearning: launch content',
    trigger: `${prefix} a.o_wslides_js_slides_list_slide_link:contains(Exercise)[href$="?fullscreen=1"]`,
    run: "click",
},
{
    content: 'eLearning: check uploaded pdf presence and perform comparison',
    trigger: (backend ? '.o_iframe:iframe ' : '') + '.o_wslides_fs_content :iframe #PDFSlideViewer',
    run: async (helpers) => {
        if (await compareBase64Content(helpers.anchor.getAttribute('data-slideurl'), 'Exercise.pdf', 'application/pdf', testPdf)) {
            helpers.anchor.classList.add('o_wslides_tour_pdf_upload_success');
        }
    },
}, {
    content: 'eLearning: check uploaded pdf content',
    trigger: `${prefix}.o_wslides_fs_content :iframe #PDFSlideViewer.o_wslides_tour_pdf_upload_success`,
    run: "click",
}, {
    content: 'eLearning: back to course',
    trigger: `${prefix}.o_wslides_fs_sidebar_header a:contains("Déboulonnate")`,
    run: "click",
}, {
    content: 'eLearning: check course page',
    trigger: `${prefix}.o_wslides_course_main`,
}];
};

var addExistingCourseTag = function (backend = false) {
    const prefix = backend ? ':iframe ' : '';
	return [
        ...clickOnAddTagDropdown(prefix),
{
    content: 'eLearning: select advanced tag',
    trigger: prefix + 'div.o_select_menu_item_label:contains("Advanced")',
    run: "click",
}, {
    content: 'eLearning: add existing course tag',
    trigger: prefix + 'footer.modal-footer a:contains("Add")',
    run: "click",
}, {
	content: 'eLearning: check that modal is closed',
	trigger: prefix + 'body:not(.modal-open)',
}];
};

var addNewCourseTag = function (courseTagName, backend) {
    const prefix = backend ? ':iframe ' : '';
    return [
        ...clickOnAddTagDropdown(prefix),
        {
    content: 'eLearning: add a new course tag',
	trigger: prefix + 'input.dropdown-item:first',
	run: "edit 123",
}, {
    content: 'eLearning: click on create this tag',
    trigger: prefix + 'i:contains("123")',
    run: "click",
},{
    content: 'eLearning: click on tag group dropdown',
	trigger: prefix + 'button.o_select_menu_toggler:last',
    run: "click",
}, {
	content: 'eLearning: select Tags tag group',
    trigger: prefix + 'div.o_select_menu_item_label:contains("Tags")',
    run: "click",
}, {
    content: 'eLearning: add new course tag',
    trigger: prefix + 'footer.modal-footer a:contains("Add")',
    run: "click",
}, {
	content: 'eLearning: check that modal is closed',
	trigger: prefix + 'body:not(.modal-open)',
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
