# odoo 觀念 - activity

建議觀看影片, 會更清楚:smile:

[Youtube Tutorial - odoo 手把手教學 - activity](https://youtu.be/_i4yLHrXRdg)

建議在閱讀這篇文章之前, 請先確保了解看過以下的文章 (因為都有連貫的關係)

[odoo 手把手建立第一個 addons](https://github.com/twtrubiks/odoo-demo-addons-tutorial/tree/master/demo_odoo_tutorial)

本篇文章主要介紹 odoo 中的 activity 這部份

## 說明

在 odoo 中, 肯定會常常看到 activity, 也就是如下圖的地方

![alt tag](https://i.imgur.com/AIlIG2b.png)

因為要先定義一個 activity 的 data,  所以先來看 [data/mail_data.xml](data/mail_data.xml)

```xml
......
<data noupdate="0">
  <record id="mail_act_approval" model="mail.activity.type">
      <field name="name">Activity Approval</field>
      <field name="icon">fa-dollar</field>
      <field name="res_model_id" ref="demo_activity.model_demo_activity"/>
  </record>
</data>
......
```

`name` 定義 activity 的名稱.

`icon` 定義 icon.

`res_model_id` 選擇對應的 model.

這個 activity 的 record 也可以在 odoo 中找到,

路徑為 Technical -> Email -> Activity Types

![alt tag](https://i.imgur.com/K6mubdq.png)

![alt tag](https://i.imgur.com/X98vjmh.png)

也可以進去修改相關的設定

![alt tag](https://i.imgur.com/xxToZSP.png)

再來看 [models/models.py](models/models.py)

```python
......
class DemoActivity(models.Model):
    _name = "demo.activity"
    _description = "Demo Activity"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='name', required=True)
    employee_id = fields.Many2one(
        'hr.employee', string="Employee", required=True)

    def button_activity_schedule(self):
        self.activity_schedule(
            'demo_activity.mail_act_approval',
            user_id = self.sudo().employee_id.user_id.id,
            note = 'my note',
            summary = 'my summary')

    def button_activity_feedback(self):
        self.activity_feedback(
            ['demo_activity.mail_act_approval'])

    def button_activity_unlink(self):
        self.activity_unlink(
            ['demo_activity.mail_act_approval'])

```

注意 `_inherit = ['mail.thread', 'mail.activity.mixin']`

這繼承是必須的哦, 不然你的 activity 是會失效的:smile:

這是所謂的 prototype inheritance,

可參考之前的文章以及影片 [demo_prototype_inheritance](https://github.com/twtrubiks/odoo-demo-addons-tutorial/tree/master/demo_prototype_inheritance).

最重要的就是這3個 function,

分別展示 `activity_schedule` `activity_feedback` `activity_unlink`

`activity_schedule`

指定 activity_schedule 給特定的人

```python
self.activity_schedule(
    'demo_activity.mail_act_approval',
    user_id = self.sudo().employee_id.user_id.id,
    note = 'my note',
    summary = 'my summary')
```

`demo_activity.mail_act_approval` 代表 activity id.

`user_id` 代表 user.

`note` 代表 note.

`summary` 代表 summary.

當點選範例的 activity_schedule

![alt tag](https://i.imgur.com/AD48O0S.png)

底下會顯示 activity

![alt tag](https://i.imgur.com/1af8U1V.png)

狀態列也會顯示有一個 activity

![alt tag](https://i.imgur.com/LYkQdkP.png)

`activity_feedback`

同意(done)這個 activity

當點選範例的 activity_feedback

![alt tag](https://i.imgur.com/NXdAALh.png)

底下會顯示 activity 狀態

![alt tag](https://i.imgur.com/OtNzxqC.png)

`activity_unlink`

取消 activity

![alt tag](https://i.imgur.com/IEoHNhc.png)

這功能和直接點選 Cancel 是一樣的 ( activity 會消失 )

![alt tag](https://i.imgur.com/ZzCNX4p.png)

也請記得設定 security

[security/ir.model.access.csv](security/ir.model.access.csv)

[security/security.xml](security/security.xml)

來看 [views/view.xml](views/view.xml)

```xml
......
    <record id="view_activity_form" model="ir.ui.view">
          <field name="name">demo.activity.form</field>
          <field name="model">demo.activity</field>
          <field eval="25" name="priority"/>
          <field name="arch" type="xml">
              <form string="Demo Activity">
                <header>
                    <button name="button_activity_schedule" string="activity schedule" type="object" class="oe_highlight"/>
                    <button name="button_activity_unlink" string="activity unlink" type="object" class="oe_highlight"/>
                    <button name="button_activity_feedback" string="activity feedback" type="object" class="oe_highlight"/>
                </header>
                <sheet>
                    <group>
                        <field name="name"/>
                        <field name="employee_id"/>
                    </group>
                </sheet>

                <div class="oe_chatter">
                    <field name="message_follower_ids" widget="mail_followers"/>
                    <field name="activity_ids" widget="mail_activity"/>
                    <field name="message_ids" widget="mail_thread"/>
                </div>

              </form>
          </field>
    </record>
......
```

`<button name="button_activity_schedule" string="activity schedule" type="object" class="oe_highlight"/>`

`name` 就是對應 model 中的 function 的名稱, 像這邊就是對應 `demo.activity` model 中的

`button_activity_schedule` function.

`string` 定義 button 的名稱.

最後的這段之前也說過了,

```xml
<div class="oe_chatter">
    <field name="message_follower_ids" widget="mail_followers"/>
    <field name="activity_ids" widget="mail_activity"/>
    <field name="message_ids" widget="mail_thread"/>
</div>
```

就是顯示下面的那段

![alt tag](https://i.imgur.com/7L9wkDx.png)

最後記得也要設定 `__manifest__.py` 哦:smile:

注意需要 depend `mail`:exclamation::exclamation:

```python
......
  {
    ......
    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'hr'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/mail_data.xml',
        'views/menu.xml',
        'views/view.xml',
    ],
    'application': True,
}
```