import re
import sys
import threading
import pyautogui
import pygetwindow as gw
import time
import os


def switch_to_window(window_title):
    """按标题切换到窗口."""
    try:
        # 获取所有窗口的标题
        all_windows = gw.getAllTitles()

        # 查找与提供的标题匹配的窗口
        matching_windows = [title for title in all_windows if window_title.lower() in title.lower()]

        if not matching_windows:
            print(f"没有找到标题包含 '{window_title}' 的窗口")
            return

        # 选择第一个匹配窗口
        target_window_title = matching_windows[0]
        target_window = gw.getWindowsWithTitle(target_window_title)[0]

        # 尝试激活窗口
        if not target_window.isActive:
            target_window.activate()

        if not target_window.isMinimized:
            target_window.restore()  # 如果窗口最小化了，先还原它
        else:
            target_window.minimize()  # 如果已经是最小化状态，则再次最小化后还原可确保窗口被激活
            target_window.restore()

        print(f"已切换到窗口: {target_window_title}")
    except Exception as e:
        print(f"无法激活窗口: {e}")


# 创建一个事件对象，用于控制线程停止
stop_event = threading.Event()


def action_space(stop_event):
    """每隔一段时间按空格键(攻击)，直到设置停止事件."""
    print("action_space 线程已启动")
    try:
        while not stop_event.is_set():
            pyautogui.press('space', interval=0.005)
    except Exception as e:
        print(f"action_space 线程发生异常: {e}")
    finally:
        print("action_space 线程结束")


def thread_space():
    """启动线程."""
    print("运行 space 线程...")
    thread = threading.Thread(target=action_space, args=(stop_event,), daemon=True)
    thread.start()


def start_monitor_thread():
    """启动监控图像线程"""
    print("运行 monitor 线程...")
    monitor_thread = threading.Thread(target=monitor_image, daemon=True)
    monitor_thread.start()


def action(solution):
    """根据提供的解决方案执行按键操作."""
    try:
        direction = solution.get('direction', 'r-l')  # 默认为 "r-l"
        a_presses = solution.get('a', [])
        d_presses = solution.get('d', [])
        interval = solution.get('interval', 0.2)

        # 根据 direction 定义按键顺序
        if direction == "l-r":
            first_list, second_list = a_presses, d_presses
            first_key, second_key = 'a', 'd'
        else:  # "r-l" 或其他情况
            first_list, second_list = d_presses, a_presses
            first_key, second_key = 'd', 'a'

        # 执行第一个列表
        for presses in first_list:
            for _ in range(presses):
                pyautogui.press(first_key, interval=interval)

        # 执行第二个列表
        for presses in second_list:
            for _ in range(presses):
                pyautogui.press(second_key, interval=interval)

    except Exception as e:
        stop_event.set()
        print(f"发生未知异常，抛出异常类：action()，异常信息：{e}")


def extract_number(filename):
    """从文件名中提取数字以帮助排序."""
    match = re.search(r'(\d+)', filename)
    return int(match.group()) if match else -1


def resource_path(relative_path):
    """ 获取附加资源的绝对路径 """
    try:
        # PyInstaller创建的临时文件夹，测试是否在bundle中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def start_game():
    """通过激活窗口并单击开始鼠标来启动游戏."""
    try:
        switch_to_window('MiSideFull')
        time.sleep(1)
        loc = find_image("0.png", 0.95, 0.3)
        if loc is not None:
            pyautogui.moveTo(loc[0] + loc[2] // 2, loc[1] + loc[3] // 2)  # 移动到图像中心
            thread_space()
            pyautogui.click(clicks=1)
    except Exception as e:
        print(f"尝试查找图像时出错: {e}")


def find_image(image_path, confidence=0.9, stop_time=0.3):
    """以指定的置信度在屏幕上查找图像."""
    try:
        img_path = resource_path("img/" + image_path)
        location = pyautogui.locateOnScreen(img_path, grayscale=True, confidence=confidence)
        if location:
            time.sleep(stop_time)
            return location
        return None
    except Exception:
        print(f"未找到指定图像，正在重新匹配...  time:{time.time()}")


def play_game(path, timeout=5, data={}):
    """处理每张图片并执行相应的操作."""
    try:
        start_time = time.time()
        img_id, _ = os.path.splitext(os.path.basename(path))
        print(f"正在处理图像: {img_id}")

        while True:
            location = find_image(path, data.get(img_id, {}).get('confidence', 0.95),
                                  data.get(img_id, {}).get('stop_time', 0.3))
            if location:
                solution = data.get(img_id)
                if solution is None:
                    print(f"未找到对应的数据: {img_id}")
                    break
                action(solution)
                return
            elapsed_time = time.time() - start_time
            if timeout and elapsed_time >= timeout:
                print(f"处理图像 {img_id} 已超时。未找到图像。")
                return None
    except Exception as e:
        stop_event.set()
        print(f"处理图像 {img_id} 时发生未知异常：{e}")
        raise  # 重新抛出异常以查看完整的堆栈跟踪


def monitor_image(image_path="over.png", confidence=0.95):
    """守护线程，防止死循环."""
    try:
        time.sleep(8)
        print("monitor_image 线程已启动...")
        while not stop_event.is_set():
            location = find_image(image_path, confidence=confidence, stop_time=0.1)
            if location:
                print(f"检测到图像 {image_path}，准备停止程序...")
                os._exit(0)
            time.sleep(0.1)  # 每秒检查一次

    except Exception as e:
        print(f"发生错误: {e}")
    except KeyboardInterrupt:
        print("监控被用户中断.")


def main():
    """Main 函数处理目录中的所有图像."""
    filepath = os.listdir(resource_path("img"))
    if not filepath:
        print("图像文件夹为空")
        sys.exit(1)

    # 只保留 .png 文件并按文件名中的数字排序
    sorted_filepaths = sorted([f for f in filepath if f.endswith('.png')], key=extract_number)

    # 移除不需要的文件
    sorted_filepaths.remove('0.png')
    sorted_filepaths.remove('over.png')

    # 游戏数据定义
    data = {'1': {'a': [0], 'd': [4], 'direction': 'r-l', 'interval': 0.2, 'confidence': 0.95, 'stop_time': 0.3},
            '2': {'a': [4], 'd': [0], 'direction': 'l-r', 'interval': 0.2, 'confidence': 0.95, 'stop_time': 0.3},
            '3': {'a': [4], 'd': [0], 'direction': 'l-r', 'interval': 0.2, 'confidence': 0.95, 'stop_time': 0.3},
            '4': {'a': [1], 'd': [3, 1, 1], 'direction': 'r-l', 'interval': 0.2, 'confidence': 0.95, 'stop_time': 0.3},
            '5': {'a': [0], 'd': [0], 'direction': 'l-r', 'interval': 0.2, 'confidence': 0.95, 'stop_time': 0.3},
            '6': {'a': [0], 'd': [0], 'direction': 'l-r', 'interval': 0.2, 'confidence': 0.95, 'stop_time': 0.3},
            '7': {'a': [2], 'd': [0], 'direction': 'l-r', 'interval': 0.2, 'confidence': 0.95, 'stop_time': 0.3},
            '8': {'a': [0], 'd': [0], 'direction': 'l-r', 'interval': 0.2, 'confidence': 0.95, 'stop_time': 0.3},
            '9': {'a': [0], 'd': [0], 'direction': 'l-r', 'interval': 0.2, 'confidence': 0.95, 'stop_time': 0.3},
            '10': {'a': [0], 'd': [2], 'direction': 'r-l', 'interval': 0.2, 'confidence': 0.95, 'stop_time': 0.3},
            '11': {'a': [2, 1, 1], 'd': [1], 'direction': 'l-r', 'interval': 0.2, 'confidence': 0.95, 'stop_time': 0.3},
            '12': {'a': [1], 'd': [1, 1], 'direction': 'r-l', 'interval': 0.2, 'confidence': 0.95, 'stop_time': 0.3},
            '13': {'a': [0], 'd': [6], 'direction': 'r-l', 'interval': 0.2, 'confidence': 0.95, 'stop_time': 0.3},
            '14': {'a': [0], 'd': [0], 'direction': 'r-l', 'interval': 0.2, 'confidence': 0.95, 'stop_time': 0.3},
            '15': {'a': [0], 'd': [0], 'direction': 'r-l', 'interval': 0.2, 'confidence': 0.95, 'stop_time': 0.3},
            '16': {'a': [0], 'd': [0], 'direction': 'r-l', 'interval': 0.2, 'confidence': 0.95, 'stop_time': 0.3},
            '17': {'a': [0], 'd': [0], 'direction': 'r-l', 'interval': 0.2, 'confidence': 0.95, 'stop_time': 0.3},
            '18': {'a': [0], 'd': [0], 'direction': 'r-l', 'interval': 0.2, 'confidence': 0.95, 'stop_time': 0.3},
            '19': {'a': [5], 'd': [0], 'direction': 'l-r', 'interval': 0.1, 'confidence': 0.67, 'stop_time': 0.2},
            '20': {'a': [0], 'd': [0], 'direction': 'r-l', 'interval': 0.2, 'confidence': 0.95, 'stop_time': 0.3},
            '21': {'a': [0], 'd': [0], 'direction': 'r-l', 'interval': 0.2, 'confidence': 0.95, 'stop_time': 0.3},
            '22': {'a': [0], 'd': [0], 'direction': 'r-l', 'interval': 0.2, 'confidence': 0.95, 'stop_time': 0.3},
            '23': {'a': [0], 'd': [0], 'direction': 'r-l', 'interval': 0.2, 'confidence': 0.95, 'stop_time': 0.3},
            '24': {'a': [1], 'd': [2, 1, 1], 'direction': 'r-l', 'interval': 0.35, 'confidence': 0.95,
                   'stop_time': 0.3},
            '25': {'a': [1], 'd': [1, 1], 'direction': 'r-l', 'interval': 0.7, 'confidence': 0.95, 'stop_time': 0.3},
            '26': {'a': [1], 'd': [0], 'direction': 'l-r', 'interval': 0.2, 'confidence': 0.98, 'stop_time': 0.3},
            '27': {'a': [1], 'd': [1], 'direction': 'l-r', 'interval': 0.2, 'confidence': 0.95, 'stop_time': 0.3},
            '28': {'a': [1, 1], 'd': [1], 'direction': 'l-r', 'interval': 0.2, 'confidence': 0.95, 'stop_time': 0.3},
            '29': {'a': [1, 1], 'd': [1], 'direction': 'l-r', 'interval': 0.2, 'confidence': 0.95, 'stop_time': 1.3},
            '30': {'a': [0], 'd': [0], 'direction': 'r-l', 'interval': 0.05, 'confidence': 0.95, 'stop_time': 0.3},
            '31': {'a': [3], 'd': [0], 'direction': 'l-r', 'interval': 0.05, 'confidence': 0.95, 'stop_time': 0.3},
            '32': {'a': [0], 'd': [6], 'direction': 'r-l', 'interval': 0.05, 'confidence': 0.95, 'stop_time': 0.3},
            '33': {'a': [5], 'd': [1], 'direction': 'l-r', 'interval': 0.05, 'confidence': 0.95, 'stop_time': 0.3},
            '34': {'a': [1], 'd': [5], 'direction': 'r-l', 'interval': 0.05, 'confidence': 0.95, 'stop_time': 0.3},
            '35': {'a': [3], 'd': [0], 'direction': 'l-r', 'interval': 0.05, 'confidence': 0.95, 'stop_time': 0.3},
            '36': {'a': [0], 'd': [0], 'direction': 'r-l', 'interval': 0.2, 'confidence': 0.98, 'stop_time': 0.3},
            '37': {'a': [1, 1], 'd': [0], 'direction': 'r-l', 'interval': 0.3, 'confidence': 0.98, 'stop_time': 0.3},
            '38': {'a': [0], 'd': [5], 'direction': 'r-l', 'interval': 0.1, 'confidence': 0.95, 'stop_time': 1},
            '39': {'a': [6], 'd': [0], 'direction': 'l-r', 'interval': 0.05, 'confidence': 0.95, 'stop_time': 0.3},
            '40': {'a': [0], 'd': [6], 'direction': 'r-l', 'interval': 0.05, 'confidence': 0.95, 'stop_time': 0.3},
            '41': {'a': [6], 'd': [0], 'direction': 'l-r', 'interval': 0.05, 'confidence': 0.95, 'stop_time': 0.3},
            '42': {'a': [0], 'd': [3], 'direction': 'r-l', 'interval': 0.05, 'confidence': 0.95, 'stop_time': 0.3},
            '43': {'a': [0], 'd': [0], 'direction': 'r-l', 'interval': 0.2, 'confidence': 0.95, 'stop_time': 0.3},
            '44': {'a': [0], 'd': [0], 'direction': 'r-l', 'interval': 0.2, 'confidence': 0.95, 'stop_time': 0.3},
            '45': {'a': [0], 'd': [0], 'direction': 'r-l', 'interval': 0.2, 'confidence': 0.95, 'stop_time': 0.3},
            '46': {'a': [0], 'd': [0], 'direction': 'r-l', 'interval': 0.2, 'confidence': 0.95, 'stop_time': 0.3},
            }

    start_game()
    start_monitor_thread()

    for path in sorted_filepaths:
        try:
            play_game(path, timeout=4, data=data)
        except Exception as e:
            print(f"处理文件 {path} 时发生错误: {e}")

    stop_event.set()
    print(f"已处理图片数量：{len(sorted_filepaths)}")
    print(f"图片列表：{sorted_filepaths}")


if __name__ == '__main__':
    main()
