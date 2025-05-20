import os
import sys
import traci
import csv
import xml.etree.ElementTree as ET
from xml.dom import minidom

# 配置参数
CAV_RATIO = 0.1
INTERVAL_DURATION = 3600  # 1小时（单位：秒）
ROU_FILE = r"F:\HK_traffic_flow - new0117\HK_traffic_flow - new0117\test.rou.xml"  # 原始字符串处理路径
SIMULATION_TIME = 10800    # 保持原3小时仿真
DETECTORS_FILE = r'F:\HK_traffic_flow - new0117\HK_traffic_flow - new0117\detectors.add.50%.xml'
CSV_FILE_PATH = r"F:\HK_traffic_flow - new0117\HK_traffic_flow - new0117\test_route_results_1.csv"
OUTPUT_CSV = "vehicle_edges.csv"

# 检查SUMO环境变量
if 'SUMO_HOME' not in os.environ:
    sys.exit("请定义SUMO_HOME环境变量")
else:
    sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))

# 加载检测器（保持原功能）
def load_defined_detectors(detectors_file):
    tree = ET.parse(detectors_file)
    return [det.attrib['id'] for det in tree.findall('inductionLoop')]

# 生成路由文件（关键修复点）
def generate_route_file(csv_path):
    def parse_csv():
        route_data = []
        with open(csv_path, 'r', encoding='utf-8-sig') as f:  # 处理BOM
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError("CSV文件为空或格式错误")
                
            for row in reader:
                try:
                    route_data.append((
                        row['Origin'].strip(),
                        row['Destination'].strip(),
                        int(row['k']),
                        int(row['Value'])
                    ))
                except KeyError as e:
                    print(f"CSV列名错误，缺少必要字段：{e}")
                    sys.exit(1)
        return route_data

    # 生成完整的XML结构
    routes = minidom.Document()
    root = routes.createElement('routes')
    routes.appendChild(root)  # 关键修复：必须将root添加到文档
    
    # 完整车辆类型参数（修复参数缺失）
    vtype_params = {
        'HDV': {
            'vClass': 'passenger',
            'color': 'yellow',
            'minGap': '2.5',
            'accel': '2.6',
            'decel': '4.5',
            'maxSpeed': '33.33',
            'lcStrategic': '1',
            'lcCooperative': '1',
            'lcSpeedGain': '1',
            'lcAssertive': '0.75',
            'tau': '1.2',
            'speedFactor': 'norm(1,0.05)'
        },
        'HDV_new': {
            'vClass': 'passenger',
            'color': 'yellow',
            'carFollowModel': 'Krauss',
            'sigma': '0.5',
            'tau': '1.4',
            'minGap': '2.5',
            'accel': '2.6',
            'decel': '4.0',
            'maxSpeed': '22.22',
            'length': '5'
        },
        'CAV': {
            'vClass': 'passenger',
            'color': 'blue',
            'minGap': '7.28894536',
            'accel': '1.80358659',
            'decel': '0.2542003',
            'maxSpeed': '41.31530379',
            'tau': '1.58680118',
            'carFollowModel': 'IDM',
            'laneChangeModel': 'LC2013',
            'lcStrategic': '1',
            'lcCooperative': '0.07141924624924251',
            'lcSpeedGain': '1',
            'lcAssertive': '0.75',
            'lcAccelThreshold': '1.797085455661397',
            'speedFactor': 'norm(1,0.05)'
        },
        'CAV_new': {
            'vClass': 'passenger',
            'color': 'blue',
            'carFollowModel': 'IDM',
            'tau': '1.0',               
            'minGap': '2',              
            'accel': '2.6',            
            'decel': '5.0',            
            'maxSpeed': '24.44',        
            'length': '5',
            'laneChangeModel': 'SL2015',
            'lcSpeedGainLookahead': '5',    
            'minGapLat': '0.6',            
            'lcSublane': '1.0',             
            'lcAssertive': '1.0',           
            'lcAccelLat': '1.0',            
            'lcMaxSpeedLatStanding': '1.0', 
            'lcMaxSpeedLatFactor': '1.6'         
        },
        'CAV_aggressive': {
            'vClass': 'passenger',
            'color': 'blue',
            'carFollowModel': 'IDM',
            'tau': '0.8',               
            'minGap': '1.5',              
            'accel': '2.6',            
            'decel': '5.0',            
            'maxSpeed': '24.44',        
            'length': '5',
            'laneChangeModel': 'SL2015',
            'lcSpeedGainLookahead': '3',    
            'minGapLat': '0.4',            
            'lcSublane': '1.5',             
            'lcAssertive': '1.5',           
            'lcAccelLat': '1.0',            
            'lcMaxSpeedLatStanding': '1.0', 
            'lcMaxSpeedLatFactor': '1.6'         
        }
    }

    # 添加车辆类型
    for vtype_id, params in vtype_params.items():
        elem = routes.createElement('vType')
        for attr, val in params.items():
            elem.setAttribute(attr, val)
        elem.setAttribute('id', vtype_id)
        root.appendChild(elem)

    # 生成flow元素
    route_data = parse_csv()
    if not route_data:
        print("警告：CSV文件中没有有效数据！")
        return

    for origin, dest, k, total in route_data:
        if total <= 0:
            continue
        
        cav_num = round(total * CAV_RATIO)
        hdv_num = total - cav_num
        
        begin = k * INTERVAL_DURATION
        end = begin + INTERVAL_DURATION
        
        # 添加两种车流
        for typ, num in [('CAV_aggressive', cav_num), ('HDV_new', hdv_num)]:
            if num <= 0:
                continue
            
            flow = routes.createElement('flow')
            flow.setAttribute('id', f"{origin}_{dest}_{typ}_{k}".replace(' ', ''))
            flow.setAttribute('type', typ)
            flow.setAttribute('from', origin)
            flow.setAttribute('to', dest)
            flow.setAttribute('begin', str(begin))
            flow.setAttribute('end', str(end))
            flow.setAttribute('number', str(num))
            root.appendChild(flow)
    
    # 确保目录存在
    os.makedirs(os.path.dirname(ROU_FILE), exist_ok=True)
    
    # 写入文件（修复缩进问题）
    with open(ROU_FILE, 'w', encoding='utf-8') as f:
        xml_str = routes.toprettyxml(indent='    ', encoding='utf-8').decode('utf-8')
        # 移除多余空行
        xml_str = '\n'.join([line for line in xml_str.split('\n') if line.strip()])
        f.write(xml_str)
    print(f"成功写入 {len(route_data)} 条路线数据到 {ROU_FILE}")

# 运行仿真（修复文件写入）
def run_simulation():
    try:
        traci.start([
            os.path.join(os.environ['SUMO_HOME'], 'bin', 'sumo'),
            "-c", "test.sumocfg", 
            "--time-to-teleport", "-1",
            "--route-files", ROU_FILE,
            "--emission-output", "emissions.xml"  # 添加该参数后SUMO会输出车辆排放信息到 emissions.xml
        ])
    except traci.FatalTraCIError as e:
        print(f"启动失败：{e}")
        sys.exit(1)
    
    # 以下代码保持原样，用于采集车辆与路段的交互数据
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        f.write("VehicleID,EdgeID,TimeStep,VehicleType\n")
    
    visited_edges = {}
    
    try:
        for step in range(SIMULATION_TIME):
            traci.simulationStep()
            
            records = []
            for veh_id in traci.vehicle.getIDList():
                try:
                    current_edge = traci.vehicle.getRoadID(veh_id)
                    veh_type = traci.vehicle.getTypeID(veh_id)
                    
                    if veh_id not in visited_edges:
                        visited_edges[veh_id] = set()
                    
                    if current_edge not in visited_edges[veh_id]:
                        records.append([veh_id, current_edge, step, veh_type])
                        visited_edges[veh_id].add(current_edge)
                except traci.TraCIException:
                    continue
            
            if records:
                with open(OUTPUT_CSV, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerows(records)
            
            if (step + 1) % 600 == 0:
                print(f"进度：{step+1}/{SIMULATION_TIME} 秒 | 当前车辆数：{len(traci.vehicle.getIDList())}")
                
    finally:
        traci.close()


# 主流程
if __name__ == "__main__":
    # 步骤1：生成车辆文件
    generate_route_file(CSV_FILE_PATH)
    
    # 步骤2：运行仿真
    print("启动SUMO仿真...")
    run_simulation()
    print(f"仿真完成，数据已保存至：{OUTPUT_CSV}")