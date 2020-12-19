[![License](https://img.shields.io/badge/license-LGPL--3.0-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0-standalone.html)

# Add custom buttons in tree views

该模块可以为列表视图添加额外的操作按钮，而非 `server actions` 的按钮一样显示在 `Action` 下拉按钮列表中。

## Usage

- 在定义窗口动作（`ir.actions.act_window`）时，在 `context` 中添加 `{'tree': {'buttons': [{'name': 'My Action', 'classes': 'oe_link', 'action': 'act_name'}]}}`

```xml
<!-- 在该例中，会在打开的列表视图的导入按钮旁新增一个名为 My Action 的按钮，点击按钮将会执行 my.model 模型中定义的方法 act_name -->
...
<record id="action_open_view" model="ir.actions.act_window">
    ...
    <field name="res_model">my.model</field>
    <field name="view_mode">tree,form</field>
    <field name="context">{'tree': {'buttons': [{'name': 'My Action', 'classes': 'oe_link', 'action': 'act_name'}]}}<field/>
    ...
</record>
...
```

其中 `classes` 是要为按钮添加的类，多个类以空格分隔；`action` 是该按钮点击时所要执行的动作，其值为当前所打开的列表视图记录所属模型下的方法的名称。

在 `buttons` 列表中可以定义多个按钮的数据，为列表视图同时添加多个操作按钮。

## Bug Tracker

如果遇到任何问题，欢迎在 [GitHub Issues](https://github.com/cognichain/odoo-basic-extension/issues) 进行反馈。

## Credits

### Contributors

- Ruter <i@ruterly.com>

### Maintainer

<img src="./static/description/icon.png" width="20%" alt="深圳市知链科技有限公司" />

该模块由深圳市知链科技有限公司开发及维护。