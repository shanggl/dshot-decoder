# DShot Protocol Decoder

sigrok/libsigrokdecode 协议解码器插件，用于解码 DShot ESC（电子调速器）通信协议。

## 功能特性

### 协议支持

- **DShot150** - 150kbps 传输速率
- **DShot300** - 300kbps 传输速率
- **DShot600** - 600kbps 传输速率

### 工作模式

- **单向模式 (Unidirectional)** - 仅解码飞控发送给 ESC 的油门帧
- **双向模式 (Bidirectional)** - 同时解码 ESC 返回的 eRPM 遥测数据

### 核心功能

| 功能 | 描述 |
|------|------|
| 帧解码 | 完整解码 16 位 DShot 帧（11 位油门 + 1 位遥测请求 + 4 位 CRC） |
| CRC 校验 | 实时检测 CRC 错误并标注 |
| 特殊命令识别 | 自动识别 0-47 号特殊命令（如 MOTOR_STOP、BEEP、ESC_INFO 等） |
| eRPM 遥测 | 双向模式下解码 ESC 返回的 eRPM 数据 |
| 多通道支持 | 支持 1-4 通道同时解码（四轴飞行器） |
| 采样率警告 | 采样率不足时自动警告 |

### 输出信息

每个 DShot 帧输出以下信息：

- **油门值** - 0-2047 范围
- **特殊命令名称** - 如 `MOTOR_STOP`、`BEEP_1` 等
- **遥测请求标志** - 是否请求 ESC 遥测
- **CRC 状态** - CRC 校验通过/失败
- **eRPM 值** - 双向模式下显示电机转速

## 适用的逻辑分析仪

本解码器兼容所有 [sigrok](https://sigrok.org/) 项目支持的逻辑分析仪硬件，包括但不限于：

### 推荐硬件

| 硬件 | 采样率推荐 | 备注 |
|------|-----------|------|
| Saleae Logic 8/16 | 50 MS/s+ | 官方支持，稳定性好 |
| DreamSourceLab DSLogic | 100 MS/s+ | 开源硬件，性价比高 |
| FX2LP-based (Clone) | 24 MS/s+ | 通用 USB 逻辑分析仪 |
| sigrok 支持的任何硬件 | ≥ 10× 比特率 | 参见 [sigrok 硬件兼容列表](https://sigrok.org/wiki/Supported_hardware) |

### 采样率要求

| DShot 变体 | 比特率 | 最低采样率 | 推荐采样率 |
|------------|--------|-----------|-----------|
| DShot150 | 150 kbps | 1.5 MS/s | 3 MS/s+ |
| DShot300 | 300 kbps | 3 MS/s | 6 MS/s+ |
| DShot600 | 600 kbps | 6 MS/s | 12 MS/s+ |

> **注意**: 采样率应至少为比特率的 10 倍，以确保可靠解码。采样率过低时解码器会显示警告。

### 软件

- [PulseView](https://sigrok.org/wiki/PulseView) - 图形化信号分析软件
- [sigrok-cli](https://sigrok.org/wiki/Sigrok-cli) - 命令行工具

## 安装方法

### 前置要求

1. 已安装 sigrok/PulseView（包含 libsigrokdecode）
2. Python 3.x 环境

### 方法一：安装到系统路径（推荐）

将 `decoders/dshot` 目录复制到 sigrokdecode 的解码器目录：

**Linux:**
```bash
# 系统级安装
sudo cp -r decoders/dshot /usr/share/libsigrokdecode/decoders/

# 或用户级安装
mkdir -p ~/.local/share/libsigrokdecode/decoders/
cp -r decoders/dshot ~/.local/share/libsigrokdecode/decoders/
```

**Windows (PulseView 便携版):**
```
复制 decoders/dshot 目录到:
PulseView/share/libsigrokdecode/decoders/
```

**Windows (PulseView 安装版):**
```
复制 decoders/dshot 目录到:
C:\Program Files\sigrok\PulseView\share\libsigrokdecode\decoders\
```

**macOS:**
```bash
# Homebrew 安装的 PulseView
cp -r decoders/dshot /usr/local/Cellar/pulseview/*/share/libsigrokdecode/decoders/

# 或用户级安装
mkdir -p ~/.local/share/libsigrokdecode/decoders/
cp -r decoders/dshot ~/.local/share/libsigrokdecode/decoders/
```

### 方法二：使用环境变量

```bash
# 设置解码器搜索路径
export SIGROKDECODE_DIR=/path/to/dshot-decoder-plugin/decoders
```

### 验证安装

**使用 sigrok-cli:**
```bash
sigrok-cli --show -P dshot
```

**使用 PulseView:**
1. 打开 PulseView
2. 点击 "Add protocol decoder"
3. 在列表中查找 "DShot"

## 使用方法

### PulseView 图形界面

1. 连接逻辑分析仪并采集信号
2. 点击 **Add protocol decoder** → 选择 **DShot**
3. 配置解码器参数：
   - **variant**: DShot150 / DShot300 / DShot600
   - **mode**: unidirectional / bidirectional
   - **num_channels**: 1-4（电机数量）

4. 将逻辑通道连接到 DShot 数据线
5. 解码结果显示在波形上方

### sigrok-cli 命令行

**基本用法:**
```bash
sigrok-cli -i capture.sr -P dshot:variant=DSHOT300:mode=unidirectional
```

**双向模式:**
```bash
sigrok-cli -i capture.sr -P dshot:variant=DSHOT300:mode=bidirectional
```

**四通道解码:**
```bash
sigrok-cli -i capture.sr -P dshot:variant=DSHOT300:num_channels=4
```

**输出 Python 格式（用于堆叠解码器）:**
```bash
sigrok-cli -i capture.sr -P dshot -B dshot=python
```

## 配置选项

| 选项 | 值 | 默认值 | 描述 |
|------|-----|--------|------|
| variant | DSHOT150, DSHOT300, DSHOT600 | DSHOT300 | DShot 协议版本 |
| mode | unidirectional, bidirectional | unidirectional | 工作模式 |
| num_channels | 1, 2, 3, 4 | 1 | 电机/通道数量 |

## DShot 协议参考

### 帧结构 (FC → ESC)

```
┌─────────────────────────────────────────────────────┐
│  Bit 15-5  │   Bit 4   │    Bit 3-0    │
│  Throttle  │ Telemetry │     CRC       │
│  (11 bits) │  Request  │   (4 bits)    │
└─────────────────────────────────────────────────────┘
```

- **Throttle (11 bits)**: 0-47 为特殊命令，48-2047 为油门值
- **Telemetry Request (1 bit)**: 请求 ESC 返回遥测数据
- **CRC (4 bits)**: 校验和

### 特殊命令

| 值 | 命令 | 描述 |
|----|------|------|
| 0 | MOTOR_STOP | 电机停止 |
| 1-5 | BEEP_1~5 | 蜂鸣器 |
| 6 | ESC_INFO | 请求 ESC 信息 |
| 7-8 | SPIN_DIRECTION | 旋转方向 |
| 20 | SPIN_DIRECTION_NORMAL | 正常旋转方向 |
| 21 | SPIN_DIRECTION_REVERSED | 反向旋转方向 |

### 时序参数

| 参数 | DShot150 | DShot300 | DShot600 |
|------|----------|----------|----------|
| T1H (高电平-1) | 5.00 µs | 2.50 µs | 1.25 µs |
| T0H (高电平-0) | 2.50 µs | 1.25 µs | 0.625 µs |
| 位周期 | 6.67 µs | 3.33 µs | 1.67 µs |
| 帧周期 | 106.7 µs | 53.3 µs | 26.7 µs |

## 故障排除

### 常见问题

**Q: 解码器不显示任何数据**

检查：
1. 采样率是否足够高（≥ 10× 比特率）
2. 通道是否正确连接到 DShot 信号线
3. 信号电平是否正确（通常为 3.3V 或 5V）

**Q: 显示 CRC 错误**

可能原因：
1. 采样率过低导致时序误差
2. 信号质量差（噪声、反射）
3. DShot 变体选择错误

**Q: 双向模式下没有 eRPM 数据**

检查：
1. ESC 是否支持双向 DShot
2. 飞控是否正确配置双向模式
3. 遥测请求位是否设置

## 参考链接

- [sigrok 官网](https://sigrok.org/)
- [PulseView 文档](https://sigrok.org/wiki/PulseView)
- [DShot 协议规范 (Betaflight)](https://betaflight.com/docs/development/API/Dshot)
- [BLHeli DShot 命令参考](https://blheli.gitbook.io/blheli-32-manual/dshot-command-reference)

## 许可证

GNU General Public License v3 or later (GPLv3+)
