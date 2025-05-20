import os
import sys
import traci
import csv
import xml.etree.ElementTree as ET
import random  # 新增 random 模块用于随机选择车辆类型

# 检查SUMO_HOME环境变量
if 'SUMO_HOME' not in os.environ:
    sys.exit("请定义SUMO_HOME环境变量")
else:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sumo_gui = os.path.join(os.environ['SUMO_HOME'], 'bin\\sumo-gui')
    sys.path.append(tools)

# 加载检测器
def load_defined_detectors(detectors_file):
    tree = ET.parse(detectors_file)
    root = tree.getroot()
    return [child.attrib['id'] for child in root.findall('inductionLoop')]

detectors_file_path = 'C:/Users/yuyazhao/Desktop/HK_traffic_flow - new0117/detectors.add.50%.xml'
defined_detectors = load_defined_detectors(detectors_file_path)

# 加载 CSV 文件数据
def load_route_data(csv_file):
    route_data = []
    with open(csv_file, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file, delimiter=',')  # 逗号分隔符
        print("CSV 文件列名:", reader.fieldnames)  # 打印列名
        for row in reader:
            origin = row['Origin'].strip()  # 去除可能的空格
            destination = row['Destination'].strip()
            k = int(row['k'])  # 时间间隔
            value = int(row['Value'])
            route_data.append((origin, destination, k, value))
    return route_data


# 生成所有可能的路线
def generate_routes():
    od_list = [f"OD{i}" for i in range(1, 16)]  # 生成 OD1, OD2, ..., OD15
    for origin in od_list:
        for destination in od_list:
            if origin != destination:  # 排除起点和终点相同的情况
                route_id = f"{origin}{destination}"  # 生成唯一的 route ID
                try:
                    traci.route.add(route_id, [origin, destination])  # 添加路线
                except traci.exceptions.TraCIException as e:
                    print(f"Route {route_id} could not be added: {e}")


# 根据 CSV 数据生成车辆流
def generate_vehicle_flow(route_data, interval_duration, total_simulation_time):
    intervals = total_simulation_time // interval_duration  # 计算时间区间数
    for origin, destination, k, value in route_data:
        route_id = f"{origin}{destination}"  # 使用 CSV 文件中的 origin 和 destination
        if value > 0:
            # 根据 k 值来确定发车的时间间隔
            interval_start_time = k * interval_duration  # 计算车辆的发车时间
            time_step_gap = interval_duration / value  # 每辆车的发车间隔
            for vehicle_index in range(value):
                depart_time = interval_start_time + vehicle_index * time_step_gap
                vehicle_id = f"{k}_{route_id}_{vehicle_index + 1}"  # 生成车辆 ID

                # 随机选择车辆类型：50% HDV，50% CAV
                if random.random() < 0.5:
                    vehicle_type = "HDV"
                else:
                    vehicle_type = "CAV"

                try:
                    traci.vehicle.add(vehicle_id, routeID=route_id, depart=depart_time, typeID=vehicle_type)
                except traci.exceptions.TraCIException as e:
                    print(f"Vehicle {vehicle_id} could not be added: {e}")


# 加载 CSV 文件
csv_file_path = "C:/Users/yuyazhao/Desktop/HK_traffic_flow - new0117/test_route_results.csv"  
route_data = load_route_data(csv_file_path)  # 调用加载函数

# 仿真启动
sumoBinary = sumo_gui
traci.start([sumoBinary, "-c", "test.sumocfg", "--time-to-teleport", "-1"])

# 初始化 CSV 文件
output_csv_path = "vehicle_edges.csv"
with open(output_csv_path, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(["VehicleID", "EdgeID", "TimeStep", "VehicleType"])  # 新增 VehicleType 列

# 定义一个字典，记录每辆车访问过的边
visited_edges = {}

# 运行仿真并记录车辆边信息
simulation_time = 10800  # 仿真时间（秒）
interval_duration = 180  # 每个 interval 为 3 分钟（180 秒）

with open(output_csv_path, mode='a', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    generate_routes()
    generate_vehicle_flow(route_data, interval_duration, simulation_time)

    for step in range(simulation_time):
        traci.simulationStep()
        vehicle_ids = traci.vehicle.getIDList()
        for vehicle_id in vehicle_ids:
            current_edge = traci.vehicle.getRoadID(vehicle_id)
            vehicle_type = traci.vehicle.getTypeID(vehicle_id)  # 获取车辆类型
            if vehicle_id not in visited_edges:
                visited_edges[vehicle_id] = set()  # 初始化该车辆的访问边集合

            if current_edge in visited_edges[vehicle_id]:
                continue

            writer.writerow([vehicle_id, current_edge, step, vehicle_type])  # 记录车辆类型
            visited_edges[vehicle_id].add(current_edge)  # 添加到已访问集合

        if (step + 1) % 100 == 0:
            print(f"当前仿真时间：{step + 1} 步")

traci.close()
print(f"仿真完成，车辆路径数据已保存到 {output_csv_path}")