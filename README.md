## 简洁版的Near Validator席位监控脚本

## 开发语言：Python

## 运行环境要求

1. 安装near-cli(https://github.com/near/near-cli)，并登录你的Near主账号。 
2. 安装python 3.6以上
3. Clone本库：https://github.com/crackerli/near-validator-monitor.git

## 脚本用法

1. 用文本编辑器打开near_stake_monitor.py
2. 找到字段stakingPoolId, 并改为自己的staking pool id
3. 找到字段masterAccountId, 并改为自己的master account id
4. 找到nodeUrl,并改为你自己运行validator节点的ip和端口(因为在测试环境中,Near网络的RPC服务很不稳定，所以建议使用自己的validator节点进行token操作)
5. 找到epochLength, 然后根据节点运行的具体网络环境设置不同的值，如betanet时epochLength=10000, testnet和mainnet时epochLength=42000
6. 以前台程序(python near_stake_monitor.py)或者服务形式运行脚本(如下配置)

## 以服务形式运行此脚本

1. 用文本编辑器打开near_monitor_bot.service, 找到ExecStart所在行，将python地址和脚本地址改为自己实际地址
1. 将near_monitor_bot.service拷贝到/etc/systemd/system/目录下(此处需要sudo权限)
3. 运行sudo systemctl start near_monitor_bot启动服务
4. 启动成功后，可以使用sudo journalctl -u near_monitor_bot.service -b查看植入的输出

## 测试
可以手动stake或unstake来测试脚本是否工作正常，当然，最好在epoch切换的前一刻来测试最好，因为大部分时候脚本是在睡眠状态。

## 后记
其他要根据网络的token质押情况动态调整我们质押数量，只需要关注T+2, 也就是near proposals命令列出来的网络统计，而这个网络统计又是实时变化的，例如有新节点加入，一些节点质押了更多的token或者取消了很多token，seat price都会随之动态变化，我们真正要关心的时epoch切换的一瞬间网络的token质押情况，所以，当我们的bot一运行，就会预先设置一次token stake，然后一直睡眠，到估计的epoch切换时间的前几分钟，bot会被重新唤醒，由于epoch切换的精确时间我们预估不到，所以我们的质量量当然也是完全准确的，会有一个向上的小小浮动


