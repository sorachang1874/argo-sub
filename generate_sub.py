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

# 2. 获取 CF 优选 IP
ip_api_url = "https://raw.githubusercontent.com/ymyuuu/IPDB/main/bestcf.txt"
try:
    response = requests.get(ip_api_url, timeout=10)
    ips = response.text.strip().split('\n')
    valid_ips = [ip.strip() for ip in ips if ip.strip() and ':' not in ip][:30] 
except Exception as e:
    print(f"获取优选IP失败: {e}")
    valid_ips = ["104.16.160.1", "104.18.2.2"]

# 3. 组装 Clash YAML 代理节点 (Proxies) 列表
proxies = []
proxy_names = []

for i, ip in enumerate(valid_ips):
    node_name = f"🇺🇸 Argo-优选-{i+1}"
    proxy_names.append(node_name)
    
    # 将 vmess 属性映射到 Clash 格式
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

# 4. 构建完整的 Clash YAML 配置文件
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

# 5. 写入文件 (注意后缀改成了 .yaml)
with open("sub.yaml", "w", encoding='utf-8') as f:
    f.write(clash_config)

print(f"成功生成 Clash 专属配置 sub.yaml！")
