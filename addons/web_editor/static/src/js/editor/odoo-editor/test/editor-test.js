import './spec/utils.test.js';
import './spec/align.test.js';
import './spec/color.test.js';
import './spec/editor.test.js';
import './spec/copyPaste.test.js';
import './spec/list.test.js';
import './spec/link.test.js';
import './spec/format.test.js';
import './spec/insertHTML.test.js';
import './spec/fontAwesome.test.js';
import './spec/tabs.test.js';
import './spec/autostep.test.js';
import './spec/urlRegex.test.js';
import './spec/collab.test.js';
import './spec/odooFields.test.js';
import './spec/powerbox.test.js';
/* global mocha */

mocha.run(failures => {
    if (failures) {
        for (const faillureElement of [...document.querySelectorAll('.test.fail')]) {
            const clonedFaillureElement = faillureElement.cloneNode(true);
            clonedFaillureElement.querySelector('a').remove();
            console.error(
                [
                    clonedFaillureElement.querySelector('h2').innerText,
                    clonedFaillureElement.querySelector('.error').innerText,
                ].join('\n\n'),
            );
        }

        // Better visualisation of invisible (ZWS & TABS) character in test
        // report.
        const report = document.querySelector("#mocha-report");
        const allErrors = report.querySelectorAll('.test.fail .error');
        allErrors.forEach((errorEl) => {
            let errorElHtml = errorEl.outerHTML
            errorElHtml = errorElHtml.replaceAll('//zws//', '<b class="zws">zws</b>');
            errorElHtml = errorElHtml.replaceAll('//TAB//', '<b class="tab">Tab</b>');
            errorEl.outerHTML = errorElHtml;
        });
    } else {
        console.log('test successful');
    }

});
