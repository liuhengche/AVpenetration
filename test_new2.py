import os
import csv
import xml.etree.ElementTree as ET
from xml.dom import minidom

# 配置文件参数
CAV_RATIO = 0.5  # CAV占比
HDV_RATIO = 1 - CAV_RATIO
INTERVAL_DURATION = 3600  # 1小时（单位：秒）
ROU_FILE = "C:/Users/yuyazhao/Desktop/HK_traffic_flow - new0117/test.rou.xml"

def load_route_data(csv_file):
    """加载CSV数据并验证格式"""
    route_data = []
    with open(csv_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        required_columns = {'Origin', 'Destination', 'k', 'Value'}
        
        # 验证列名
        if not required_columns.issubset(reader.fieldnames):
            missing = required_columns - set(reader.fieldnames)
            raise ValueError(f"CSV文件缺少必要列：{missing}")
        
        for row in reader:
            # 数据清洗和类型转换
            origin = row['Origin'].strip()
            destination = row['Destination'].strip()
            k = int(row['k'])
            value = int(row['Value'])
            
            if value < 0:
                raise ValueError(f"无效的车辆数：{value}（行：{row})")
                
            route_data.append((origin, destination, k, value))
    
    return route_data

def generate_flow_elements(route_data):
    """生成XML流程元素"""
    flows = []
    
    # 添加车辆类型定义
    flows.extend([
        '<!-- 车辆类型定义 -->',
        '<vType id="HDV" vClass="passenger" color="yellow" minGap="2.5" accel="2.6" decel="4.5" maxSpeed="33.33" lcStrategic="1" lcCooperative="1" lcSpeedGain="1" lcAssertive="0.75" tau="1.2" speedFactor="norm(1,0.05)"/>',
        '<vType id="CAV" vClass="passenger" color="blue" minGap="7.28894536" accel="1.80358659" decel="0.2542003" maxSpeed="41.31530379" tau="1.58680118" carFollowModel="IDM" laneChangeModel="LC2013" lcStrategic="1" lcCooperative="0.07141924624924251" lcSpeedGain="1" lcAssertive="0.75" lcAccelThreshold="1.797085455661397" speedFactor="norm(1,0.05)"/>'
    ])
    
    # 生成流量元素
    for origin, destination, k, total in route_data:
        if total == 0:
            continue
            
        # 计算各类型车辆数（四舍五入）
        cav_num = round(total * CAV_RATIO)
        hdv_num = total - cav_num
        
        # 时间区间计算
        begin = k * INTERVAL_DURATION
        end = (k + 1) * INTERVAL_DURATION
        
        # 生成flow元素
        if cav_num > 0:
            flow_id = f"{origin}_{destination}_CAV_{k}"
            flows.append(
                f'<flow id="{flow_id}" type="CAV" from="{origin}" to="{destination}" begin="{begin}" end="{end}" number="{cav_num}"/>'
            )
            
        if hdv_num > 0:
            flow_id = f"{origin}_{destination}_HDV_{k}"
            flows.append(
                f'<flow id="{flow_id}" type="HDV" from="{origin}" to="{destination}" begin="{begin}" end="{end}" number="{hdv_num}"/>'
            )
    
    return flows

def generate_rou_xml(flows):
    """生成格式化的XML文件"""
    xml_content = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<routes>'
    ]
    
    xml_content.extend(['    ' + line for line in flows])
    xml_content.append('</routes>')
    
    # 美化XML格式
    rough_xml = '\n'.join(xml_content)
    reparsed = minidom.parseString(rough_xml)
    pretty_xml = reparsed.toprettyxml(indent="    ", encoding="UTF-8")
    
    # 移除自动生成的XML声明
    pretty_xml = b'\n'.join([line for line in pretty_xml.splitlines() if line.strip()])
    
    with open(ROU_FILE, 'wb') as f:
        f.write(pretty_xml)

def main():
    # 加载数据
    csv_path = "C:/Users/yuyazhao/Desktop/HK_traffic_flow - new0117/test_route_results.csv"
    route_data = load_route_data(csv_path)
    
    # 生成流程元素
    flows = generate_flow_elements(route_data)
    
    # 生成最终文件
    generate_rou_xml(flows)
    print(f"成功生成路由文件：{ROU_FILE}（总生成条目：{len(flows)-2}）")  # 减去类型定义

if __name__ == "__main__":
    main()