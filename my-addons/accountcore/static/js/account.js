// 科目项目
odoo.define('accountcore.main_models', ['web.Class'], function (require) {
    "use strict";
    var Class = require('web.Class');
    var BaseNameId = Class.extend({
        init: function (name, id) {
            this.name = name;
            this.id = id;
        }
    });
    // 机构/主体
    var Org = BaseNameId.extend({
        init: function (name, id) {
            this._super.apply(this, [name, id]);
        }
    });
    // 会计科目
    var Account = BaseNameId.extend({
        init: function (name,number,id) {
            this.number = number;
            this._super.apply(this,[name,id]);
        }
    });
    // 科目类别
    var AccountClass = BaseNameId.extend({
        init: function (name, id, number) {
            this.number = number;
            this._super.apply(this, [name, id]);
        }
    });
    // 项目
    var Item = BaseNameId.extend({
        init: function (name, id, itemClass) {
            this.itemClass = itemClass;
            this._super.apply(this, [name, id]);
        }
    });
    // 项目类别
    var ItemClass = BaseNameId.extend({
        init: function (name, id) {
            this._super.apply(this, [name, id]);
        }
    });
    // 会计科目和项目
    var AccountItem = Class.extend({
        init: function (account, item, items = []) {
            this.account = account;
            this.item = item;
            this.items = items;
        }
    });
    // 科目余额表金额
    var BalanceAmount = Class.extend({
        init: function (beginD = 0, beginC = 0, thisD = 0, thisC = 0, endD = 0, endC = 0, yearD = 0, yearC = 0) {
            // 期初借方
            this.beginD = beginD;
            this.beginC = beginC;
            // 本期借方发生额
            this.thisD = thisD;
            this.thisC = thisC;
            this.endD = endD;
            this.endC = endC;
            // 本年累计借方(取开始日期当年)
            this.yearD = yearD;
            this.yearC = yearC;
        }
    });
    // 一条余额记录
    var BalanceLine = Class.extend({
        init: function (accountItem, balanceAmount) {
            this.accountItem = accountItem;
            this.balanceAmount = balanceAmount;
        }
    });
    // 借贷金额
    var Amountdc = Class.extend({
        init: function (damount = 0, camount = 0) {
            this.d = admount;
            this.c = camount;
        }
    });
    return {
        Org: Org,
        Account: Account,
        Item: Item,
        ItemClass: ItemClass,
        AccountItem: AccountItem,
        BalanceAmount: BalanceAmount,
        BalanceLine: BalanceLine,
        Amountdc: Amountdc,
    }
});