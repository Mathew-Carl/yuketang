# yuketang
雨课堂多用户版本, 支持自动签到, 自动答题(自动获取其他用户答案)


安装依赖：
--
```shell
pip install -r requirements.txt 
```
 - pyzbar 为二维码识别库，部分 Linux 安装不全，需用软件包管理工具安装 zbar 相关依赖；始终失败请注释[1](util.py#L32-L38)和[2](util.py#L6-L8)

运行：
--
```shell
python main.py
```

### 配置文件
*config.json*
```shell
{
  "yuketang": {
    "domain": "pro.yuketang.cn",
    "classroomCodeList": ["JZOJ5C", "G84UAB"],
    "classroomWhiteList": [],
    "clashroomBlackList": ["2023秋-机器学习-0", "2023清华实践"],
    "clashroomStartTimeDict": {
      "2023秋-机器学习-0": {"1": "08:00", "2": "13:30"},
      "2023清华实践": {"1": "13:30"}
    },
    "wx": false,
    "dd": false,
    "fs": false,
    "an": false,
    "ppt": false,
    "si": false,
    "timeout": 30
  },
  "send": {
    "wx": {
      "touser": "@all",
      "agentId": "####",
      "secret": "####",
      "companyId": "####",
      "msgLimit": 500,
      "dataLimit": 20971520
    },
    "dd": {
      "appKey": "####",
      "appSecret": "####",
      "robotCode": "####",
      "openConversationId": "####",
      "msgLimit": 3000,
      "dataLimit": 20971520
    },
    "fs": {
      "appId": "####",
      "appSecret": "####",
      "openId": "####",
      "msgLimit": 10000,
      "dataLimit": 31457280
    },
    "timeout": 30
  },
  "util": {
    "threads": 20,
    "timezone": "Asia/Shanghai",
    "timeout": 30
  }
    "users":[
    {
      "name": "####",
      "openId": "####"
    },
    {
      "name": "####",
      "openId":"####"
    }
  ]
}
```

说明：
--
 - 首次运行将下载雨课堂登录二维码（可推送到客户端），微信扫码获取 cookie，有效期约两周；有效期少于两天时，每小时初将发送二维码提醒，请及时扫码更新，谨防失效后消息轰炸<br>
 - 支持多线程监听，每 30 秒使用班级邀请码/课堂暗号进入新班级、扫描新课堂，随后自动签到、下载课件（pdf）、打印题目及答案、查看当前 PPT 进度<br>
 - 签到方式为通过“正在上课”提示进入课堂<br>
 - 题目答案会从users列表里的用户提交的答案中获取(不需要单独向本程序提交,本程序自动抓包解析users列表用户在雨课堂提交的答案),实现一人在雨课堂提交答案,全组提交相同答案<br>
 - 此项目为本大学生自制自用,有较大不足,请多海涵<br>
 - 答题时会造成消息狂轰乱炸,请不要介意,犯懒<br>
 - 如果觉得好用,可以给我个star嘛<br>
 - 未来可能会添加作业未完成进行推送提示(如果我不犯懒并且用得上的情况下)<br>
 - 未来不会添加AI答题,个人感觉正确率太低,如果正确率上升可能会添加<br>
 - 如果没发现答案不会进行提交,请注意<br>
 - 多用户仅适配了飞书推送,由于本人太萌新没用过钉钉和企业微信(本人第一个作品),所以暂不支持,用过的可以来找我以便添加适配<br>
 - 大部分代码来自thuhollow2/Hetangyuketang,十分感谢大佬的代码,基本没怎么动主体部分,包括说明文档也是改自原作者<br>

### 配置文件
 - 默认设置雨课堂域名为 `pro.yuketang.cn`<br>
 - `classroomCodeList` 为班级邀请码/课堂暗号列表，每 30 秒尝试加入班级，加入成功或班级不存在将自动去除，班级满员时可启用此功能待成员退出抢占名额<br>
 - `classroomWhiteList`/`clashroomBlackList`/`clashroomStartTimeDict` 等使用的课程名，可在[雨课堂首页](https://pro.yuketang.cn/v2/web/index)课程标签里查找，具体如[图](classroomName.png)中红框所示，采用完全匹配，为空时不启用<br>
 - `clashroomStartTimeDict` 中，1-7 代表周一-周日，当日时间值不为空且此时早于该值不签到，数字或时间为空不启用<br>
 - `yuketang` 中，`an` 设置为 `true` 时自动答题，`ppt` 设置为 `true` 时自动下载 PPT，`si` 设置为 `true` 时实时推送 PPT 进度<br>
  - users中填入需要的用户和相应的对话ID<br>
 - 启用企业微信推送需[注册企业](https://work.weixin.qq.com/wework_admin/register_wx?from=myhome)、[创建应用](https://work.weixin.qq.com/wework_admin/frame#apps/createApiApp)、[**配置企业可信IP**](https://work.weixin.qq.com/wework_admin/frame#apps)，并设置 `yuketang` 的 `wx` 为 `true`、在 `send` 填充 `wx` 的 `agentId`、`secret`、`companyId`，默认设置 `touser` 为企业全体成员<br>
 - 启用钉钉推送需[注册钉钉开发者账号](https://open-dev.dingtalk.com/)、[创建并发布企业内部应用（应用内创建机器人）](https://open-dev.dingtalk.com/fe/app#/corp/app)、[获取群会话OpenConversationId](https://open.dingtalk.com/document/isvapp/get-the-openconversationid-of-the-group-session)、机器人添加进群，并设置 `yuketang` 的 `dd` 为 `true`、在 `send` 填充 `dd` 的 `appKey`、`appSecret`、`robotCode`、`openConversationId`<br>
 - 启用飞书推送需[注册飞书开发者账号、创建并发布企业内部应用、请注意不要个人版本要创建企业,并把你的小伙伴邀请进企业哦](https://open.feishu.cn/app?lang=zh-CN)、[开启机器人能力](https://open.feishu.cn/document/faq/trouble-shooting/how-to-enable-bot-ability)、[获取OpenId](https://open.feishu.cn/document/server-docs/im-v1/message/create)、开通权限（[*以应用的身份发消息*](https://open.feishu.cn/document/server-docs/im-v1/message/create)，[*获取与上传图片或文件资源*](https://open.feishu.cn/document/server-docs/im-v1/file/create)），并设置 `yuketang` 的 `fs` 为 `true`、在 `send` 填充 `fs` 的 `appId`、`appSecret`、`openId`<br>
 - 单次推送有大小限制，超过将分块传输，默认设置 `send`：<br>
 
    | 推送方式 | 消息限制 (`msgLimit`) | 文件限制 (`dataLimit`) | 
    | -------- | -------- | -------- |
    | 企业微信 (`wx`) | 500字符 (500) | 20MB (20971520) |
    | 钉钉 (`dd`) | 3000字符 (3000) | 20MB (20971520) |
    | 飞书 (`fs`) | 10000字符 (10000) | 30MB (31457280) |
 - `util` 中，`threads` 为 PPT 文件下载的线程数，`timezone` 选择时区<br>
 - `timeout` 为连接超时秒数<br>
### 声明
 - 项目尚有许多不足<br>
 - 修改自 [thuhollow2/Hetangyuketang](https://github.com/thuhollow2/Hetangyuketang)<br>
