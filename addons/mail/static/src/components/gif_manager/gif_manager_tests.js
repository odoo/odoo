/** @odoo-module **/

import Composer from '@mail/components/composer/composer';
import { create } from '@mail/model/model_field_command';
import {
    afterEach,
    afterNextRender,
    createRootComponent,
    beforeEach,
    start,
} from '@mail/utils/test_utils';

const components = { Composer };

QUnit.module('gif_manager', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('gif_manager', {}, function () {
QUnit.module('gif_manager_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.data.tenorApiKey = 'test';

        this.createComposerComponent = async (composer, otherProps) => {
            const props = Object.assign({ composerLocalId: composer.localId }, otherProps);
            await createRootComponent(this, components.Composer, {
                props,
                target: this.widget.el,
            });
        };

        this.start = async params => {
            const { afterEvent, env, widget } = await start(Object.assign({}, params, {
                data: this.data,
            }));
            this.afterEvent = afterEvent;
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('Composer has a gif button', async function (assert) {
    assert.expect(1);

    await this.start();
    const thread = this.env.models['mail.thread'].create({
        composer: create({ isLog: false }),
        id: 20,
        model: 'res.partner',
    });
    await this.createComposerComponent(thread.composer);

    assert.containsOnce(document.body, '.o_Composer_buttonGif', "should have gif button");
});


QUnit.test('Click on the gif button open the gif manager', async function(assert) {
    assert.expect(4);

    await this.start();
    const thread = this.env.models['mail.thread'].create({
        composer: create({ isLog: false }),
        id: 20,
        model: 'res.partner',
    });
    await this.createComposerComponent(thread.composer);

    await afterNextRender(() =>
        document.querySelector('.o_Composer_buttonGif').click()
    );

    assert.containsOnce(document.body, '.o_GifManager', "should have gif manager");
    assert.containsOnce(document.body, '.o_GifFavoriteCategory', "should have gif favorite section");
    assert.containsOnce(document.body, '.o_GifCategories', "should have gif category list");
    assert.containsOnce(document.body, '.o_GifCategory', "should have gif category");
});

QUnit.test('Open category', async function(assert) {
    assert.expect(2);

    await this.start();
    const thread = this.env.models['mail.thread'].create({
        composer: create({ isLog: false }),
        id: 20,
        model: 'res.partner',
    });
    await this.createComposerComponent(thread.composer);
    await afterNextRender(() => {
        document.querySelector('.o_Composer_buttonGif').click();
    });
    await afterNextRender(() => {
        document.querySelector('.o_GifCategoryTitle').click();
    });
    assert.containsOnce(document.body, '.o_GifList', "should have gif list");
    assert.strictEqual(document.querySelector('.gifSearchInput input').value, 'cry', "Search should contain the category search term");
});

QUnit.test('Perform a gif search', async function(assert) {
    assert.expect(1);

    await this.start();
    const thread = this.env.models['mail.thread'].create({
        composer: create({ isLog: false }),
        id: 20,
        model: 'res.partner',
    });
    await this.createComposerComponent(thread.composer);
    await afterNextRender(() => {
        document.querySelector('.o_Composer_buttonGif').click();
    });

    await afterNextRender(() => {
        document.querySelector(`.gifSearchInput input`).focus();
        document.execCommand('insertText', false, "cry");
    });
    assert.containsOnce(document.body, '.o_GifList', "should have gif search list");
});

QUnit.test('Insert a gif inside the composer', async function(assert) {
    assert.expect(1);

    await this.start();
    const thread = this.env.models['mail.thread'].create({
        composer: create({ isLog: false }),
        id: 20,
        model: 'res.partner',
    });
    await this.createComposerComponent(thread.composer);
    await afterNextRender(() => {
        document.querySelector('.o_Composer_buttonGif').click();
    });

    await afterNextRender(() => {
        document.querySelector(`.gifSearchInput input`).focus();
        document.execCommand('insertText', false, "cry");
    });
    await afterNextRender(() => {
        document.querySelector('.o_Gif .gif').click();
    });
    assert.strictEqual(
        document.querySelector('.o_ComposerTextInput_textarea').value,
        ' https://tenor.com/view/tom-y-jerry-tom-and-jerry-meme-sad-cry-gif-18054267',
        "Should have a gif inserted inside the composer"
    );
});

QUnit.test('Open favorites gifs', async function(assert) {
    assert.expect(1);

    this.data['mail.gif_favorite'].records.push({
        gif_id: 15579685,
    });
    await this.start({ debug: true });
    const thread = this.env.models['mail.thread'].create({
        composer: create({ isLog: false }),
        id: 20,
        model: 'res.partner',
    });
    await this.createComposerComponent(thread.composer);
    await afterNextRender(() => {
        document.querySelector('.o_Composer_buttonGif').click();
    });
    await afterNextRender(() =>{
        document.querySelector('.o_GifFavoriteCategory .o_GifFavoriteOverlay').click();
    });
    assert.containsOnce(document.body, '.o_GifFavorite', 'Gif manager contain the favorite list');
});

});
});
});
