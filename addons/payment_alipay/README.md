# payment_alipay
alipay for odoo

this module still in development, use it in production on your own risk

any feedback should be thankful.

if you want technical support, please contact the author and check the link http://item.taobao.com/item.htm?spm=a1z10.1-c.w4004-10020970078.16.EvfHHC&id=44624969034



Odoo 8.0 支付宝模块中文使用<br>
<br>
一、安装payment_alipay模块前的注意事项：<br>
<br>
1、要注意观察，是否得到两个文件夹，如果是下载zip包，则解压后注意路径问题，要把模块放addons目录下层，而不是在下下层目录。确保目录路径为addons\payment_allpay\以及addons\payment_alipay\都能看到README.md该文件。<br>
2、首先到https://github.com/odoo-cn/payment/tree/8.0 下载得到8.0版本的pay两个：支付宝(alipay)和欧付宝(allpay)，<br>
3、然后到odoo里更新模块列表：【设置】->【模块】下的【更新模块列表】，更新后，可搜到alipay和allpay两个模块。<br>
二、配置alipay和allpay：<br>
<br>
alipay的设置步骤如下：<br>
1、odoo中，【设置】->【Payments 】下【 Payment Acquirers 】会看到有【Alipay】，点它，画面会转一下到alipay支付宝模块配置页的画面；<br>
2、其中特别注意：支付宝的开发者注册成功后，会得到一些参数，例如以下四样：<br>
 Alipay Partner ID<br>
Alipay Partner Key<br>
Alipay Seller Email <br>
Alipay Interface Type <br>
将这四样填写进去即可实现利用odoo开网上商城，然后用alipay支付宝来收款。<br>
以上，简述一下。如有不当，请跟贴。<br>


