import './spec/utils.test.js';
import './spec/align.test.js';
import './spec/editor.test.js';
import './spec/list.test.js';
import './spec/link.test.js';
import './spec/fontSize.test.js';
import './spec/insertHTML.test.js';
import './spec/fontAwesome.test.js';
import './spec/autostep.test.js';
import './spec/urlRegex.test.js';
import './spec/collab.test.js';

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
    const reportEl = document.getElementById('mocha-report');
    window.scrollTo(0, window.scrollY + reportEl.getBoundingClientRect().top);
});
