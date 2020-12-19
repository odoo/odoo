odoo.define('mail_media_repository/static/src/components/composer/composer.js', function (require) {
'use strict';

const components = {
    Composer: require('mail/static/src/components/composer/composer.js'),
    MediaSelectButton: require('mail_media_repository/static/src/components/media_select_button/media_select_button.js'),
};

const { useState } = owl;

Object.assign(components.Composer.components, {
    MediaSelectButton: components.MediaSelectButton,
});

});
