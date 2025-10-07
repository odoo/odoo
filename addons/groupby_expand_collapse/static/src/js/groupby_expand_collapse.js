/** @odoo-module */
import { ListController } from "@web/views/list/list_controller";

ListController.prototype.collapselist = async function () {
  this.model.root.groups.forEach((element) => {
    if (!element.isFolded) {
      element.toggle();
    }
  });
};

// ListController.prototype.expandlist = function () {
//   this.model.root.groups.forEach((element) => {
//     if (element.isFolded) {
//       element.toggle();
//     }
//     const groups = element.list.groups;
//     if (groups && groups.length > 0) {
//       this.recusrsivelist(groups);
//     }
//   });

// };

ListController.prototype.recusrsivelist = async function (groups) {
  groups.forEach((element) => {
    if (element.isFolded) {
      element.toggle();
    }

    if (element.list.groups) {
      if (element.list.groups.length > 0) {
        this.recusrsivelist(element.list.groups);
      }
    }
  });
};



(ListController.prototype.expandlist = async function () {
  var group = this.model.root.groups;
  for (let i = 0; i < group.length; i++) {
    //toggling for the first time all the list folds
    if (group[i].isFolded) {
      await group[i].toggle();
    }
    //using inbuild toggle function to toggle

    var groupOfList = await group[i].list.model.root.groups[i].list.model.root
      .groups[i].list.groups;

    // group[i].toggle()

    await this._onClickChild(groupOfList);
  }
}),
  (ListController.prototype._onClickChild = async function (groupOfList) {
    if (groupOfList) {
      for (let j = 0; j < groupOfList.length; j++) {
        if (groupOfList[j].isFolded) {
          await groupOfList[j].toggle();
        }
        await this._onClickChild(groupOfList[j].list.groups);
      }
    }
  });
