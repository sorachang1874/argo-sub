import os
import json
import base64
import requests
import re

# 1. 解析母版节点
vmess_b64 = os.environ.get("VMESS_TEMPLATE", "")
if vmess_b64.startswith("vmess://"):
    vmess_b64 = vmess_b64[8:]

try:
    missing_padding = len(vmess_b64) % 4
    if missing_padding:
        vmess_b64 += '=' * (4 - missing_padding)
    template_json = json.loads(base64.b64decode(vmess_b64).decode('utf-8'))
except Exception as e:
    print(f"解析母版节点失败: {e}")
    exit(1)

# 2. 极其严苛的 IPv4 正则表达式
ipv4_pattern = re.compile(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')

# 3. 您的专属精选 IP 源 (已剔除停更库，更新为 raw 直链)
urls = [
    # ZhiXuanWang 的 Top10 动态 API (逗号分隔)
    "https://ip.164746.xyz/ipTop10.html",
    # ymyuuu 的主力优选 IPv4
    "https://raw.githubusercontent.com/ymyuuu/IPDB/main/BestCF/bestcfv4.txt",
    # ymyuuu 的优质反代 IP 及国家节点
    "https://raw.githubusercontent.com/ymyuuu/IPDB/main/BestProxy/bestproxy%26country.txt"
]

all_ips = set()

# 4. 工业级数据清洗引擎
for url in urls:
    try:
        response = requests.get(url, timeout=10)
        # 预处理：将逗号替换为换行，应对 ipTop10.html 的紧凑格式
        content = response.text.replace(',', '\n')
        lines = content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            # 暴力剥离法：应对 "1.1.1.1:443#US" 或 "1.1.1.1 延迟" 这种复杂脏数据
            # 依次按 空格、井号、冒号 切分，永远只取第一块最纯净的 IP
            ip_candidate = line.split()[0].split('#')[0].split(':')[0].strip()
            
            # 终极校验：过筛放入集合（自动去重）
            if ipv4_pattern.match(ip_candidate):
                all_ips.add(ip_candidate)
                
    except Exception as e:
        print(f"从 {url} 抓取异常: {e}")

# 限制池子大小，防止 Clash 加载成百上千个节点导致电脑卡顿
valid_ips = list(all_ips)[:150]

# 5. 极品保底库 (CF Anycast 官方网段)
if not valid_ips:
    print("警告：所有在线源拉取失败，启用内置保底 IP 库！")
    valid_ips = [
        "104.16.0.0", "104.17.0.0", "104.18.0.0", "104.19.0.0",
        "104.20.0.0", "104.21.0.0", "104.22.0.0", "104.24.0.0",
        "104.25.0.0", "104.26.0.0", "104.27.0.0", "172.66.0.0",
        "172.67.0.0", "162.159.0.0"
    ]

# 6. 组装 Clash YAML 代理节点
proxies = []
proxy_names = []

for i, ip in enumerate(valid_ips):
    # 如果是反代库里混进来的，名称里统一叫优选，因为 Clash 本地测速会自己分出高下
    node_name = f"🇺🇸 极速优选-{i+1}"
    proxy_names.append(node_name)
    
    proxy = f"""  - name: "{node_name}"
    type: vmess
    server: {ip}
    port: {template_json.get('port', 443)}
    uuid: {template_json.get('id', '')}
    alterId: 0
    cipher: auto
    tls: true
    servername: {template_json.get('sni', '')}
    skip-cert-verify: true
    network: ws
    ws-opts:
      path: {template_json.get('path', '/')}
      headers:
        Host: {template_json.get('host', '')}
"""
    proxies.append(proxy)

# 7. 构建完整配置
clash_config = f"""port: 7890
socks-port: 7891
allow-lan: true
mode: rule
log-level: info
ipv6: false

proxies:
{chr(10).join(proxies)}

proxy-groups:
  - name: 🚀 节点选择
    type: select
    proxies:
      - ♻️ 自动测速优选
{chr(10).join([f"      - {name}" for name in proxy_names])}
      
  - name: ♻️ 自动测速优选
    type: url-test
    url: http://www.gstatic.com/generate_204
    interval: 300
    tolerance: 50
    proxies:
{chr(10).join([f"      - {name}" for name in proxy_names])}

rules:
  - MATCH,🚀 节点选择
"""

with open("sub.yaml", "w", encoding='utf-8') as f:
    f.write(clash_config)

print(f"成功清洗并聚合 {len(valid_ips)} 个高质量 IP，已写入 sub.yaml！")
