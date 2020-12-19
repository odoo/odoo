
mxid_list = ['1f57ce5f87e402c705b8157bc6771d33', 'f10936876a8d9c3e5db362dd31248844','111']
factory_mxid_list = ['1f57ce5f87e402c705b8157bc6771d33', 'f10936876a8d9c3e5db362dd31248844','222']
delete = set(mxid_list) - set(factory_mxid_list)
insert = set(factory_mxid_list) - set(mxid_list)
update = set(mxid_list) & set(factory_mxid_list)
print(delete)
print(insert)
print(update)