import os
import json
import base64
import requests

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

# 2. 多源 CF 优选 IP 库 (可随时增删)
ip_api_urls = [
    "https://raw.githubusercontent.com/ymyuuu/IPDB/main/bestcf.txt",
    "https://raw.githubusercontent.com/vfarid/cf-ip-scanner/main/ipv4.txt",
    "https://raw.githubusercontent.com/ircfspace/cf2dns/master/list/ipv4.txt",
    # Joey 和 ygkkk 通常使用动态测速脚本而非静态列表，
    # 以上三个是圈内最稳定、由国内探针生成的静态直链库。
]

all_ips = set() # 使用 set 自动去重

# 3. 遍历所有源，抓取并清洗 IP
for url in ip_api_urls:
    try:
        response = requests.get(url, timeout=10)
        lines = response.text.strip().split('\n')
        for line in lines:
            line = line.strip()
            # 过滤掉空行、注释和 IPv6(Clash处理v6有时会报错)
            if line and not line.startswith('#') and ':' not in line:
                # 兼容某些列表带有端口和延迟的格式 (如 IP,port,latency)
                clean_ip = line.split(',')[0].strip()
                all_ips.add(clean_ip)
    except Exception as e:
        print(f"从 {url} 获取IP失败: {e}")

# 将去重后的 IP 列表转换为 list，并限制最大数量防止订阅文件过大导致客户端卡顿 (取前 60 个)
valid_ips = list(all_ips)[:60]

if not valid_ips:
    valid_ips = ["104.16.160.1", "104.18.2.2"] # 终极保底

# 4. 组装 Clash YAML
proxies = []
proxy_names = []

for i, ip in enumerate(valid_ips):
    node_name = f"🇺🇸 Argo-优选池-{i+1}"
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

# 5. 构建完整配置
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
      - ♻️ 自动优选
{chr(10).join([f"      - {name}" for name in proxy_names])}
      
  - name: ♻️ 自动优选
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

print(f"成功聚合多个源，生成 {len(valid_ips)} 个去重优选节点，并写入 sub.yaml！")
