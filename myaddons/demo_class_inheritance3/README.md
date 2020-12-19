# odoo 繼承 - class inheritance

建議觀看影片, 會更清楚:smile:

[Youtube Tutorial - odoo 繼承 - class inheritance](https://youtu.be/zgb_0MJ3q9w)

建議在閱讀這篇文章之前, 請先確保了解看過以下的文章 (因為都有連貫的關係)

[odoo 手把手建立第一個 addons](https://github.com/twtrubiks/odoo-demo-addons-tutorial/tree/master/demo_odoo_tutorial)

本篇文章主要介紹 class inheritance 這部份

## 說明

`_inherit` class inheritance

注意, 還有一個是 `_inherits`, 不要搞錯了哦.

通常 `_inherit` 是去修改或是去擴充既有的 model,

使用情境可能如下,

像是在一個既有的 model 上增加一個 fields.

覆蓋掉一個已經存在的 model 中的 fields 定義.

增加 constraints 到一個既有的 model 上.

增加額外的 method 到一個既有的 model 上.

覆蓋掉一個已經存在的 model 中的 method.

這張圖是 odoo 中繼承的種類, 今天介紹 class inheritance,

![alt tag](https://i.imgur.com/2aQ8BNh.png)

先來看 [models/models.py](models/models.py)

```python
......
class ClassInheritance(models.Model):
    _name = 'hr.expense' # 可寫可不寫
    _inherit = ['hr.expense']

    test_field = fields.Char('test_field')
......
```

目標是去繼承 `hr.expense`, 並且增加一個 `fields`.

`_name = 'hr.expense' # 可寫可不寫`

`hr.expense` 是一個既有的 model, 所以在 `__manifest__.py` 中有 depends 關係

(記得一定要寫 depends, 不然會出現錯誤:exclamation:)

```python
......
 'depends': ['hr_expense'],
......
```

`_name` 和 `_inherit` 在這邊的名稱都是一樣的,

注意, 請不要自己定義一個 `_name` (和 `_inherit` 不一致), 因為這是另一個東西(如下圖, 以後說明).

![alt tag](https://i.imgur.com/kjtCar6.png)

`_inherit = ['hr.expense']`

主要去繼承 `hr.expense`, 所以一定要有 depends:exclamation::exclamation:

當你安裝好 addons, 我們到資料庫中可以找到剛剛新增的 test_field

![alt tag](https://i.imgur.com/MOFEDXy.png)


簡單說這種繼承的方式就是在繼承的 model 上增加新功能.

[views/views.xml](views/views.xml)

```xml
......
<record id="view_expenses_tree_custom" model="ir.ui.view">
  <field name="name">hr.expense.tree.custom</field>
  <field name="model">hr.expense</field>
  <field name="inherit_id" ref="hr_expense.view_expenses_tree"/>
  <field name="arch" type="xml">
      <field name="date" position="after">
          <!-- <field name="test_field" groups="product.group_sale_pricelist" readonly="1"/> -->
          <field name="test_field"/>
      </field>

      <!-- xpath the same result -->
      <!--views/views.xml
      <xpath expr="//field[@name='date']" position="after">
          <field name="test_field" />
      </xpath>
      -->

  </field>
</record>
......
```

![alt tag](https://i.imgur.com/PobVtjJ.png)

找 fields 的時候有兩種方式可以找,

第一種, 比較簡單的方法, 直接找到 fields, 然後定義 position 即可

```xml
......
<field name="date" position="after">
  <field name="test_field"/>
</field>
......
```

第二種, 使用 xpath 的語法, 稍微比較複雜一點, 但是當你一個 view

裡面有重複的 fields 時, 就比較適合使用 xpath, 因為如果你使用第

一種方法, 會導致找不到 (有重複它會不知道要找哪一個:grimacing:)

```xml
......
<xpath expr="//field[@name='date']" position="after">
  <field name="test_field" />
</xpath>
......
```

所以可以依照自己的需求下去選擇.

[views/views.xml](views/views.xml)

form 的部份

```xml
......
<record id="hr_expense_view_form_custom" model="ir.ui.view">
    <field name="name">hr.expense.view.form.custom</field>
    <field name="model">hr.expense</field>
    <field name="inherit_id" ref="hr_expense.hr_expense_view_form"/>
    <field name="arch" type="xml">
        <field name="employee_id" position="after">
            <field name="test_field"/>
        </field>
    </field>
</record>
......
```

![alt tag](https://i.imgur.com/DXJ4xK2.png)

## 延伸閱讀

* [demo_prototype_inheritance](https://github.com/twtrubiks/odoo-demo-addons-tutorial/tree/master/demo_prototype_inheritance)

* [demo_delegation_inheritance](https://github.com/twtrubiks/odoo-demo-addons-tutorial/tree/master/demo_delegation_inheritance)