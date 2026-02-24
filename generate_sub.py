import os
import json
import base64
import requests

# 1. 从环境变量提取母版节点
vmess_b64 = os.environ.get("VMESS_TEMPLATE", "")
if vmess_b64.startswith("vmess://"):
    vmess_b64 = vmess_b64[8:]

try:
    # 修复 Base64 padding 问题
    missing_padding = len(vmess_b64) % 4
    if missing_padding:
        vmess_b64 += '=' * (4 - missing_padding)
    template_json = json.loads(base64.b64decode(vmess_b64).decode('utf-8'))
except Exception as e:
    print(f"解析母版节点失败: {e}")
    exit(1)

# 2. 从开源全网测速库获取最新的 CF 优选 IP (专门针对国内网络环境)
ip_api_url = "https://raw.githubusercontent.com/ymyuuu/IPDB/main/bestcf.txt"
try:
    response = requests.get(ip_api_url, timeout=10)
    ips = response.text.strip().split('\n')
    # 过滤空行，提取前 30 个极速 IP
    valid_ips = [ip.strip() for ip in ips if ip.strip() and ':' not in ip][:30] 
except Exception as e:
    print(f"获取优选IP失败: {e}")
    valid_ips = ["104.16.160.1", "104.18.2.2"] # 失败时的保底 IP

# 3. 批量缝合，生成新节点
final_nodes = []
for i, ip in enumerate(valid_ips):
    node = template_json.copy()
    node["add"] = ip  # 将物理连接地址替换为优选 IP
    node["ps"] = f"🇺🇸 Argo-优选-{i+1}"  # 重命名节点别名，方便在 Clash 中查看
    
    # 重新编码为 vmess 链接
    node_str = json.dumps(node, separators=(',', ':'))
    node_b64 = base64.b64encode(node_str.encode('utf-8')).decode('utf-8')
    final_nodes.append(f"vmess://{node_b64}")

# 4. 生成最终的 Clash 订阅文件 (所有节点组合后再 Base64)
sub_content = '\n'.join(final_nodes)
sub_b64 = base64.b64encode(sub_content.encode('utf-8')).decode('utf-8')

with open("sub.txt", "w") as f:
    f.write(sub_b64)

print(f"成功生成 {len(final_nodes)} 个优选节点，并写入 sub.txt！")
