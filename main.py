import webview
from agv_api import Api

api = Api()

class Bridge:
    def get_robot_info(self, ip: str):
        return api.get_robot_info(ip)
    
    def scan_network(self, subnet: str):
        return api.scan_network(subnet)
    
    def get_bins(self, ip: str, map_name: str = "default"):
        return api.get_bins(ip, map_name)
        

if __name__ == "__main__":
    bridge = Bridge()
    window = webview.create_window("AGV 派車工具", "index.html", js_api=bridge, width=1000, height=700)
    webview.start(gui="edgechromium", debug=True)
