import { OdooEditor } from '../src/OdooEditor.js';

const localStorageKey = 'odoo-editor-snippets';

function startEditor(html) {
    const editableContainer = document.getElementById('dom');
    editableContainer.innerHTML = html;
    new OdooEditor(editableContainer, {
        toolbar: document.querySelector('#toolbar'),
        autohideToolbar: true,
        defaultLinkAttributes: { target: '_blank', rel: 'ugc' },
    });

    document.querySelector('#control-panel').style.display = 'none';
    document.querySelector('.demo-editor-action').style.display = 'block';
    document.querySelector('#saved-html-list').remove();
}

function goToSnippet(key) {
    const searchParams = new URLSearchParams(window.location.search);
    searchParams.set('key', key);
    window.location.search = searchParams.toString();
}

function updateSnippet(key, value) {
    const localHtmlStored = localStorage.getItem(localStorageKey);
    const localHtmlSaved = localHtmlStored ? JSON.parse(localHtmlStored) : {};
    localHtmlSaved[key] = value;
    localStorage.setItem(localStorageKey, JSON.stringify(localHtmlSaved));
    goToSnippet(key);
}

function loadSnippet(key) {
    const localHtmlStored = localStorage.getItem(localStorageKey);
    const snippets = localHtmlStored && JSON.parse(localHtmlStored);
    const html = snippets[key];
    startEditor(html);
}

function removeSnippet(key) {
    const localHtmlStored = localStorage.getItem(localStorageKey);
    const localHtmlSaved = localHtmlStored ? JSON.parse(localHtmlStored) : {};
    delete localHtmlSaved[key];
    localStorage.setItem(localStorageKey, JSON.stringify(localHtmlSaved));
    window.location.reload();
}

function renderSnippets() {
    const snippetContainer = document.querySelector('#saved-html-list ul');
    const localHtmlStored = localStorage.getItem(localStorageKey);
    if (localHtmlStored) {
        snippetContainer.innerText = '';
        const localHtmlSaved = JSON.parse(localHtmlStored);
        for (const key of Object.keys(localHtmlSaved)) {
            const li = document.createElement('li');
            const snippetLink = document.createElement('a');
            const removeButton = document.createElement('button');
            removeButton.style.display = 'inline-block';
            removeButton.innerText = 'X';
            removeButton.addEventListener('click', () => removeSnippet(key));
            snippetLink.innerText = key;

            const url = new URL(window.location);
            const searchParams = new URLSearchParams(window.location.search);
            searchParams.set('key', key);
            url.search = searchParams.toString();
            snippetLink.href = url.href;

            li.appendChild(removeButton);
            li.appendChild(snippetLink);
            snippetContainer.appendChild(li);
        }
    } else {
        snippetContainer.style.display = 'none';
    }
}

/**
 * Quick UI to start editing
 */
const submitButtonEl = document.getElementById('textarea-submit');
submitButtonEl.addEventListener('click', () => {
    updateSnippet('last-submited', document.getElementById('textarea').value);
    goToSnippet('last-submited');
});
const useSampleEl = document.getElementById('use-sample');
useSampleEl.addEventListener('click', () => {
    startEditor(document.getElementById('sample-dom').innerHTML);
});

const key = new URLSearchParams(window.location.search).get('key');
if (key) {
    try {
        loadSnippet(key);
    } catch (e) {
        console.error(e);
    }
} else {
    renderSnippets();
}

document.querySelector('.demo-editor-action-home').addEventListener('click', () => {
    window.location.search = '';
});

document.querySelector('#save-c-html-button').addEventListener('click', () => {
    const html = document.getElementById('dom').innerHTML;
    updateSnippet(prompt('Enter a storage name for this html snippet', 'unnamed'), html);
});

document.querySelector('#start-tests').addEventListener('click', () => {
    window.location = `${window.location.href
        .split('/')
        .slice(0, -2)
        .join('/')}/test/editor-test.html`;
});
