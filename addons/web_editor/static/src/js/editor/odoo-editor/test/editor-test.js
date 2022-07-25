import './spec/utils.test.js';
import './spec/align.test.js';
import './spec/color.test.js';
import './spec/editor.test.js';
import './spec/copyPaste.test.js';
import './spec/list.test.js';
import './spec/link.test.js';
import './spec/fontSize.test.js';
import './spec/format.test.js';
import './spec/insertHTML.test.js';
import './spec/fontAwesome.test.js';
import './spec/autostep.test.js';
import './spec/urlRegex.test.js';
import './spec/collab.test.js';
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
    } else {
        console.log('test successful');
    }

    // Clean report of successful tests to ease DEV / debug
    // just add ?clean=1
    const reportEl = document.getElementById('mocha-report');
    window.scrollTo(0, window.scrollY + reportEl.getBoundingClientRect().top);
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('clean')) {
        console.log('Successful tests have been removed.');
        const report = document.querySelector("#mocha-report");

        let hr = document.createElement("hr");
        report.prepend(hr);
        let h1 = document.createElement("h1");
        h1.textContent = "Clean : Successfull tests have been removed.";
        report.prepend(h1);

        const passedTests = report.querySelectorAll('.test.pass');
        for (let el of passedTests) {
            el.remove();
        }

        const cleanUl = function () {
            const emptyUl = report.querySelectorAll('ul:empty');
            for (let ul of emptyUl) {
                ul.parentElement.remove();
            }
        };
        for (let i = 4; i > 0; i--) {
            cleanUl();
        }

        report.outerHTML = report.outerHTML.replaceAll('//zws//', '<b class="zws">zws</b>');
    }
});
