/* Copyright 2016 LasLabs Inc.
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */

odoo.define_section('web_responsive', ['web_responsive'], function(test) {
    "use strict";
    
    // It provides a base drawer compatible interface for testing
    self.initInterface = function(AppDrawer) {
        
        var $el = $('<div class="drawer drawer--left">');
        $el.append(
            $('<header role="banner">')
                .append(
                    $('<button class="drawer-toggle"><span class="drawer-hamburger-icon">')
                )
                .append(
                    $('<nav class="drawer-nav"><ul class="drawer-menu"><li class="drawer-menu-item">')
                )
                .append(
                    $('<div class="panel-title" id="appDrawerAppPanelHead">')
                )
        ).append($('<main role="main">'));
        
        self.$clickZone = $('<a class="oe_menu_leaf">');
        
        self.$secondaryMenu = $('<div><div class="o_sub_menu_content">');
        
        self.$dropdown = $('<div class="dropdown-scrollable">');
    
        $el.append(self.$clickZone)
            .append(self.$secondaryMenu)
            .append(self.$dropdown);
        
        var $document = $("#qunit-fixture");
        $document.append($el);
        
        self.drawer = new AppDrawer.AppDrawer();
        
        return $document;
        
    };
    
    self.linkGrid = function() {
        for(var i=0; i < 3; i++){
            self.drawer.$el.append(
                $('<div class="row">').append(
                    $('<a class="col-md-6" id="a_' + i + '"><span class="app-drawer-icon-app /></a>' +
                      '<a class="col-md-6" id="b_' + i + '"><span class="app-drawer-icon-app /></a>'
                      )
                )
            );
            self.drawer.$appLinks = $('a.col-md-6');
        }
    };
    
    test('It should set initialized after success init',
         function(assert, AppDrawer) {
            self.initInterface(AppDrawer);
            assert.ok(self.drawer.initialized);
         }
    );
    
    test('It should close drawer after click on clickZone',
         {asserts: 1},
         function(assert, AppDrawer) {
            self.initInterface(AppDrawer);
            self.$clickZone.click();
            var d = $.Deferred();
            setTimeout(function() {
                assert.ok(self.drawer.$el.hasClass('drawer-close'));
                d.resolve();
            }, 100);
            return d;
         }
    );
    
    test('It should collapse open secondary menus during handleClickZones',
         {asserts: 1},
         function(assert, AppDrawer) {
            self.initInterface(AppDrawer);
            self.$clickZone.click();
            var d = $.Deferred();
            setTimeout(function() {
                assert.equal(self.$secondaryMenu.attr('aria-expanded'), 'false');
                d.resolve();
            }, 100);
            return d;
         }
    );
    
    test('It should update max-height on scrollable dropdowns',
         function(assert, AppDrawer) {
            self.initInterface(AppDrawer);
            self.drawer.handleWindowResize();
            var height = $(window).height() * self.drawer.dropdownHeightFactor;
            assert.equal(
                self.$dropdown.css('max-height'),
                height + 'px'
            );
         }
    );
    
    test('It should return keybuffer + new key',
         function(assert, AppDrawer) {
            self.initInterface(AppDrawer);
            self.drawer.keyBuffer = 'TES';
            var res = self.drawer.handleKeyBuffer(84);
            assert.equal(res, 'TEST');
         }
    );
    
    test('It should clear keybuffer after timeout',
         {asserts: 1},
         function(assert, AppDrawer) {
            self.initInterface(AppDrawer);
            self.drawer.keyBuffer = 'TES';
            self.drawer.keyBufferTime = 10;
            self.drawer.handleKeyBuffer(84);
            var d = $.Deferred();
            setTimeout(function() {
                assert.equal(self.drawer.keyBuffer, "");
                d.resolve();
            }, 100);
            return d;
         }
    );
    
    test('It should trigger core bus event for drawer close',
         ['web.core'], {asserts: 1},
         function(assert, AppDrawer, core) {
            self.initInterface(AppDrawer);
            self.drawer.onDrawerOpen();
            var d = $.Deferred();
            core.bus.on('drawer.closed', this, function() {
                assert.ok(true);
                d.resolve();
            });
            self.drawer.$el.trigger({type: 'drawer.closed'});
            return d;
         }
    );
    
    test('It should set isOpen to false when closing',
         {asserts: 1},
         function(assert, AppDrawer) {
            self.initInterface(AppDrawer);
            self.drawer.onDrawerOpen();
            var d = $.Deferred();
            setTimeout(function() {
                assert.equal(self.drawer.isOpen, false);
                d.resolve();
            });
            self.drawer.$el.trigger({type: 'drawer.closed'});
            return d;
         }
    );
    
    test('It should set isOpen to true when opening',
         {asserts: 1},
         function(assert, AppDrawer) {
            self.initInterface(AppDrawer);
            var d = $.Deferred();
            self.drawer.$el.trigger({type: 'drawer.opened'});
            setTimeout(function() {
                assert.ok(self.drawer.isOpen);
                d.resolve();
            });
            return d;
         }
    );
    
    test('It should trigger core bus event for drawer open',
         ['web.core'], {asserts: 1},
         function(assert, AppDrawer, core) {
            self.initInterface(AppDrawer);
            self.drawer.onDrawerOpen();
            var d = $.Deferred();
            core.bus.on('drawer.opened', this, function() {
                assert.ok(true);
                d.resolve();
            });
            self.drawer.$el.trigger({type: 'drawer.opened'});
            return d;
         }
    );
    
    test('It should choose link to right',
         function(assert, AppDrawer) {
            self.initInterface(AppDrawer);
            self.linkGrid();
            var $appLink = $('#a_1'),
                $expect = $('#a_2'),
                $res = self.drawer.findAdjacentAppLink(
                    $appLink, self.drawer.RIGHT
                );
            assert.equal($res[0].id, $expect[0].id);
         }
    );
    
    test('It should choose link to left',
         function(assert, AppDrawer) {
            self.initInterface(AppDrawer);
            self.linkGrid();
            var $appLink = $('#a_2'),
                $expect = $('#a_1'),
                $res = self.drawer.findAdjacentAppLink(
                    $appLink, self.drawer.LEFT
                );
            assert.equal($res[0].id, $expect[0].id);
         }
    );
    
    test('It should choose link above',
         function(assert, AppDrawer) {
            self.initInterface(AppDrawer);
            self.linkGrid();
            var $appLink = $('#a_1'),
                $expect = $('#a_0'),
                $res = self.drawer.findAdjacentAppLink(
                    $appLink, self.drawer.UP
                );
            assert.equal($res[0].id, $expect[0].id);
         }
    );
    
    test('It should choose link below',
         function(assert, AppDrawer) {
            self.initInterface(AppDrawer);
            self.linkGrid();
            var $appLink = $('#a_1'),
                $expect = $('#a_2'),
                $res = self.drawer.findAdjacentAppLink(
                    $appLink, self.drawer.DOWN
                );
            assert.equal($res[0].id, $expect[0].id);
         }
    );
    
    test('It should choose first link if next on last',
         function(assert, AppDrawer) {
            self.initInterface(AppDrawer);
            self.linkGrid();
            var $appLink = $('#b_2'),
                $expect = $('#a_0'),
                $res = self.drawer.findAdjacentAppLink(
                    $appLink, self.drawer.RIGHT
                );
            assert.equal($res[0].id, $expect[0].id);
         }
    );
    
    test('It should choose bottom link if up on top',
         function(assert, AppDrawer) {
            self.initInterface(AppDrawer);
            self.linkGrid();
            var $appLink = $('#a_0'),
                $expect = $('#a_2'),
                $res = self.drawer.findAdjacentAppLink(
                    $appLink, self.drawer.UP
                );
            assert.equal($res[0].id, $expect[0].id);
         }
    );
    
    test('It should choose top link if down on bottom',
         function(assert, AppDrawer) {
            self.initInterface(AppDrawer);
            self.linkGrid();
            var $appLink = $('#a_2'),
                $expect = $('#a_0'),
                $res = self.drawer.findAdjacentAppLink(
                    $appLink, self.drawer.DOWN
                );
            assert.equal($res[0].id, $expect[0].id);
         }
    );
    
});
