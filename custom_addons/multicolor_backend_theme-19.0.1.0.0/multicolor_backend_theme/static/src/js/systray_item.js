/** @odoo-module **/

import { NavBar } from "@web/webclient/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { useState, onWillStart} from "@odoo/owl";
import { user } from "@web/core/user";

patch(NavBar.prototype, {
    setup(...args) {
        super.setup(...args);
        this.state = useState({
            theme_data: {},
            selected_theme: {}
        });
        this.editMode = false;
        this.orm = useService("orm");
        this.notification = useService('notification');
        this.current_theme = {};
        this.themes_by_id = {};
//        this.user = useService("user");
        onWillStart(async () => {
            var self = this;
            this.user = await user.hasGroup("multicolor_backend_theme.multicolor_theme_manager_access");
            const theme_data = await this.orm.searchRead('theme.config', [], ['name', 'is_theme_active', 'theme_font_color', 'theme_main_color', 'view_font_color']);
            return $.when(theme_data).then((theme_data) => {
                self.state.theme_data = theme_data;
                theme_data.forEach(theme => {
                    if (theme.is_theme_active) {
                        self.selected_theme = theme;
                    }
                    self.themes_by_id[theme.id] = theme;
                })
                if (!self.selected_theme) {
                    self.selected_theme = theme_data[0];
                    self.selected_theme.is_theme_active = true;
                }
                self.state.selected_theme = self.selected_theme;
                self.onClickApply();
            });
        });
    },
    //    Handle the onChange event for selecting a theme.
    onChangeTheme() {
        let themeId = parseInt($('.theme_select').val());
        this.state.selected_theme = this.themes_by_id[themeId];
        const colorProperties = ['theme_main_color', 'theme_font_color', 'view_font_color'];
        colorProperties.forEach(property => {
            document.getElementById(property).style.backgroundColor = this.state.selected_theme[property];
        });
        this.onChangeActive();
    },
    //    Handle the event for selecting base color.
    onClickBaseColor(){
        var self = this;
        const selectedTheme = this.themes_by_id[parseInt($('.theme_select').val())]
        const colorProperties = ['theme_main_color', 'theme_font_color', 'view_font_color'];
        colorProperties.forEach(property => {
            $('#' + property).loads({
                layout: 'hex',
                flat: false,
                enableAlpha: false,
                color: self.selected_theme.property,
                onSubmit: function(ev) {
                    let elId = $(ev.el).attr('id');
                    $('#' + elId).css('background-color', '#' + ev.hex);
                    $('#' + elId).val("#" + ev.hex);
                    $('#' + elId).hides();
                    self._onchangeColor($(ev.el), ev.hex);
                },
                onLoaded: function(ev) {
                    $('.picker').css('color', 'green');
                },
                onChange: function(ev) {
                    let elId = $(ev.el).attr('id');
                    $('#' + elId).setColor(ev.hex, false);
                }
            });
        })
    },
    //    Function to update color on backend.
    _onchangeColor(element, data) {
        let current_theme = this.themes_by_id[$('.theme_select').val()];
        let colorCode = '#' + data;
        if (colorCode != current_theme[element.attr('id')]) {
            current_theme[element.attr('id')] = colorCode;
            this.themes_by_id[current_theme.id][element.attr('id')] = '#' + data;
            let field = element.attr('id');
            this.orm.write('theme.config', [current_theme.id], {
                [field]: colorCode,
            });
        };
    },
    //    Handle the onClick event for applying the selected theme.
    async onClickApply(){
        if (this.state.selected_theme) {
            this.appliedTheme = this.state.selected_theme;
            document.documentElement.style.setProperty("--theme_main_color", this.state.selected_theme.theme_main_color);
            document.documentElement.style.setProperty("--theme_font_color", this.state.selected_theme.theme_font_color);
            document.documentElement.style.setProperty("--view_font_color", this.state.selected_theme.view_font_color);
            $('.cybro-main-menu .input-group-text').css({
                'background-color': this.state.selected_theme.theme_main_color,
                'border-color': this.state.selected_theme.theme_main_color,
                'color': this.state.selected_theme.theme_font_color,
            });
            $('.o_loading').css({
                'background-color': this.state.selected_theme.theme_main_color,
                'color': this.state.selected_theme.theme_font_color,
            });
            $('.btn-primary').css({
                'background-color': this.state.selected_theme.theme_main_color,
                'color': this.state.selected_theme.theme_font_color,
            });
            $('.o-mail-ChatWindow-header').attr('style', `background-color: ${this.state.selected_theme.theme_main_color} !important; color: ${this.state.selected_theme.theme_font_color};`);

        }
        let curr_theme_id = parseInt($('.theme_select').val());
        if (curr_theme_id){
            let result = await this.orm.call('theme.config','update_active_theme',[curr_theme_id]);
            this.themes_by_id[result['prev']].is_theme_active = false;
            this.themes_by_id[curr_theme_id].is_theme_active = true;
            this.onChangeActive();
            this.notification.add("Theme has been successfully updated",
                { type: 'success' }, 3000
            );
        };
    },
   //    Handle the onClick event for creating new theme.
    async onClickCreate(){
        let result = await this.orm.call('theme.config', 'create_new_theme',[]);
        this.state.selected_theme = result[0];
        this.state.theme_data.push(result[0]);
        this.themes_by_id[result[0].id] = result[0];
        this.onChangeActive();
    },
    //    Handle the onClick event for deleting theme.
    async onClickRemove(){
        let themeId = parseInt($('.theme_select').val());
        let currentTheme = this.themes_by_id[themeId];
        if (currentTheme.is_theme_active) {
            this.notification.add("You cannot delete an active theme.",
                { type: 'danger' }, 3000
            );
        } else {
            this.orm.unlink('theme.config', [themeId]);
            this.state.theme_data = this.state.theme_data.filter(data => data.id !== themeId);
            this.state.selected_theme = this.appliedTheme;
        };
        this.onChangeActive();
    },
    //    Function to edit name of theme.
    async onEditName() {
        this.editMode = !this.editMode;
        let themeInput = document.getElementById('themeName');
        let editIcon = document.getElementById('editIcon');
        if (this.editMode) {
            themeInput.removeAttribute('readonly');
            themeInput.style.backgroundColor = '#e4eaec';
            editIcon.classList.remove('fa-pencil');
            editIcon.classList.add('fa-check');
        } else {
            themeInput.setAttribute('readonly', 'readonly');
            themeInput.style.backgroundColor = 'white';
            editIcon.classList.remove('fa-check');
            editIcon.classList.add('fa-pencil');
            this.orm.write('theme.config', [this.state.selected_theme.id] , {
                name: themeInput.value
            });
            this.state.selected_theme.name = themeInput.value;
            this.themes_by_id[this.state.selected_theme.id].name = themeInput.value;
        };
    },
    //    Function to set active selected theme.
    onChangeActive() {
        document.getElementById('active_theme').style.display = this.state.selected_theme.is_theme_active ? 'block' : 'none';
    },
});