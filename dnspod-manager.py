import tkinter as tk
from tkinter import ttk, messagebox
import requests
import webbrowser

class DNSPodAPI:
    """封装 DNSPod 传统 API（v1）"""
    BASE_URL = "https://dnsapi.cn/"

    def __init__(self, login_token):
        self.login_token = login_token  # 格式: "ID,Token"
        self.headers = {
            "User-Agent": "DNSPod GUI/1.0 (your_email@example.com)"
        }
        self.common_params = {
            "login_token": self.login_token,
            "format": "json",
            "lang": "cn",
            "error_on_empty": "yes"
        }

    def _post(self, action, data=None):
        url = self.BASE_URL + action
        params = self.common_params.copy()
        if data:
            params.update(data)
        try:
            resp = requests.post(url, data=params, headers=self.headers, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"status": {"code": "-1", "message": f"请求异常: {str(e)}"}}

    def get_domain_list(self):
        result = self._post("Domain.List")
        if result.get("status", {}).get("code") == "1":
            return result.get("domains", [])
        else:
            raise Exception(result.get("status", {}).get("message", "未知错误"))

    def get_record_list(self, domain_id):
        result = self._post("Record.List", {"domain_id": domain_id})
        if result.get("status", {}).get("code") == "1":
            return result.get("records", [])
        else:
            raise Exception(result.get("status", {}).get("message", "未知错误"))

    def create_record(self, domain_id, sub_domain, record_type, value, ttl=600, line="默认"):
        data = {
            "domain_id": domain_id,
            "sub_domain": sub_domain,
            "record_type": record_type,
            "record_line": line,
            "value": value,
            "ttl": ttl
        }
        return self._post("Record.Create", data)

    def modify_record(self, domain_id, record_id, sub_domain, record_type, value, ttl=600, line="默认"):
        data = {
            "domain_id": domain_id,
            "record_id": record_id,
            "sub_domain": sub_domain,
            "record_type": record_type,
            "record_line": line,
            "value": value,
            "ttl": ttl
        }
        return self._post("Record.Modify", data)

    def delete_record(self, domain_id, record_id):
        data = {"domain_id": domain_id, "record_id": record_id}
        return self._post("Record.Remove", data)

    def set_record_status(self, domain_id, record_id, status):
        data = {"domain_id": domain_id, "record_id": record_id, "status": status}
        return self._post("Record.Status", data)

    def set_record_remark(self, domain_id, record_id, remark):
        """修改记录备注（仅限主账号）"""
        data = {"domain_id": domain_id, "record_id": record_id, "remark": remark}
        return self._post("Record.Remark", data)


class Application:
    def __init__(self, root):
        self.root = root
        self.root.title("DNSPod 域名记录管理")
        self.root.geometry("900x700")  # 加宽以适应备注列
        self.api = None
        self.current_domain_id = None
        self.current_domain_name = None
        self.records = []

        # ---------- 认证区域 ----------
        frame_auth = ttk.LabelFrame(root, text="认证信息", padding=10)
        frame_auth.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(frame_auth, text="API ID:").grid(row=0, column=0, sticky=tk.W)
        self.entry_id = ttk.Entry(frame_auth, width=20)
        self.entry_id.grid(row=0, column=1, padx=5)

        ttk.Label(frame_auth, text="API Token:").grid(row=0, column=2, sticky=tk.W, padx=(20,0))
        self.entry_token = ttk.Entry(frame_auth, width=30, show="*")
        self.entry_token.grid(row=0, column=3, padx=5)

        self.btn_login = ttk.Button(frame_auth, text="连接", command=self.login)
        self.btn_login.grid(row=0, column=4, padx=10)

        # ---------- GitHub 链接 ----------
        link_label = tk.Label(
            frame_auth,
            text="GitHub: wlzwd",
            fg="blue",
            cursor="hand2",
            font=("TkDefaultFont", 9, "underline")
        )
        link_label.grid(row=0, column=5, sticky='e', padx=10)
        link_label.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/wlzwd"))

        # ---------- 域名选择 ----------
        frame_domain = ttk.LabelFrame(root, text="选择域名", padding=10)
        frame_domain.pack(fill=tk.X, padx=10, pady=5)

        self.domain_var = tk.StringVar()
        self.combo_domain = ttk.Combobox(frame_domain, textvariable=self.domain_var, state="readonly")
        self.combo_domain.pack(fill=tk.X)
        self.combo_domain.bind("<<ComboboxSelected>>", self.on_domain_selected)

        # ---------- 记录列表 ----------
        frame_list = ttk.LabelFrame(root, text="解析记录", padding=10)
        frame_list.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 增加“备注”列
        columns = ("ID", "子域名", "类型", "记录值", "TTL", "线路", "状态", "备注")
        self.tree = ttk.Treeview(frame_list, columns=columns, show="headings")
        self.tree.heading("ID", text="记录ID")
        self.tree.heading("子域名", text="子域名")
        self.tree.heading("类型", text="类型")
        self.tree.heading("记录值", text="记录值")
        self.tree.heading("TTL", text="TTL")
        self.tree.heading("线路", text="线路")
        self.tree.heading("状态", text="状态")
        self.tree.heading("备注", text="备注")

        # 设置列宽
        self.tree.column("ID", width=60)
        self.tree.column("子域名", width=120)
        self.tree.column("类型", width=80)
        self.tree.column("记录值", width=180)
        self.tree.column("TTL", width=60)
        self.tree.column("线路", width=80)
        self.tree.column("状态", width=60)
        self.tree.column("备注", width=150)

        scrollbar = ttk.Scrollbar(frame_list, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self.on_record_selected)

        # ---------- 操作区域 ----------
        frame_ops = ttk.LabelFrame(root, text="操作", padding=10)
        frame_ops.pack(fill=tk.X, padx=10, pady=5)

        # 第一行：基本字段
        ttk.Label(frame_ops, text="子域名:").grid(row=0, column=0, sticky=tk.W)
        self.entry_sub = ttk.Entry(frame_ops, width=15)
        self.entry_sub.grid(row=0, column=1, padx=5)

        ttk.Label(frame_ops, text="类型:").grid(row=0, column=2, sticky=tk.W, padx=(10,0))
        self.combo_type = ttk.Combobox(frame_ops, values=["A", "AAAA", "CNAME", "MX", "TXT", "SRV", "CAA"], width=8)
        self.combo_type.grid(row=0, column=3, padx=5)
        self.combo_type.set("A")

        ttk.Label(frame_ops, text="记录值:").grid(row=0, column=4, sticky=tk.W, padx=(10,0))
        self.entry_value = ttk.Entry(frame_ops, width=20)
        self.entry_value.grid(row=0, column=5, padx=5)

        ttk.Label(frame_ops, text="TTL:").grid(row=0, column=6, sticky=tk.W, padx=(10,0))
        self.entry_ttl = ttk.Entry(frame_ops, width=6)
        self.entry_ttl.grid(row=0, column=7, padx=5)
        self.entry_ttl.insert(0, "600")

        # 第二行：备注
        ttk.Label(frame_ops, text="备注:").grid(row=1, column=0, sticky=tk.W)
        self.entry_remark = ttk.Entry(frame_ops, width=40)
        self.entry_remark.grid(row=1, column=1, columnspan=7, padx=5, sticky=tk.W)

        # 第三行：按钮
        btn_frame = ttk.Frame(frame_ops)
        btn_frame.grid(row=2, column=0, columnspan=8, pady=5)

        self.btn_add = ttk.Button(btn_frame, text="添加", command=self.add_record)
        self.btn_add.pack(side=tk.LEFT, padx=5)

        self.btn_update = ttk.Button(btn_frame, text="修改当前选中", command=self.update_record)
        self.btn_update.pack(side=tk.LEFT, padx=5)

        self.btn_delete = ttk.Button(btn_frame, text="删除当前选中", command=self.delete_record)
        self.btn_delete.pack(side=tk.LEFT, padx=5)

        self.btn_toggle_status = ttk.Button(btn_frame, text="切换状态", command=self.toggle_record_status)
        self.btn_toggle_status.pack(side=tk.LEFT, padx=5)

        self.btn_update_remark = ttk.Button(btn_frame, text="更新备注", command=self.update_remark)
        self.btn_update_remark.pack(side=tk.LEFT, padx=5)

        self.btn_refresh = ttk.Button(btn_frame, text="刷新列表", command=self.refresh_records)
        self.btn_refresh.pack(side=tk.LEFT, padx=5)

        # 状态栏
        self.status = ttk.Label(root, text="就绪", relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(fill=tk.X, padx=10, pady=5)

        # 初始禁用
        self.set_operation_state(False)

    def set_operation_state(self, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.combo_domain.config(state="readonly" if enabled else tk.DISABLED)
        self.entry_sub.config(state=state)
        self.combo_type.config(state=state)
        self.entry_value.config(state=state)
        self.entry_ttl.config(state=state)
        self.entry_remark.config(state=state)
        self.btn_add.config(state=state)
        self.btn_update.config(state=state)
        self.btn_delete.config(state=state)
        self.btn_toggle_status.config(state=state)
        self.btn_update_remark.config(state=state)
        self.btn_refresh.config(state=state)

    def login(self):
        api_id = self.entry_id.get().strip()
        token = self.entry_token.get().strip()
        if not api_id or not token:
            messagebox.showerror("错误", "请输入 API ID 和 Token")
            return
        login_token = f"{api_id},{token}"
        self.api = DNSPodAPI(login_token)
        try:
            domains = self.api.get_domain_list()
            if not domains:
                messagebox.showinfo("提示", "该账号下没有域名")
                self.combo_domain['values'] = []
                self.set_operation_state(False)
                return
            self.domain_list = domains
            domain_names = [d['name'] for d in domains]
            self.combo_domain['values'] = domain_names
            if domain_names:
                self.combo_domain.set(domain_names[0])
                self.on_domain_selected()
            self.set_operation_state(True)
            self.status.config(text=f"连接成功，共 {len(domains)} 个域名")
        except Exception as e:
            messagebox.showerror("连接失败", str(e))
            self.set_operation_state(False)

    def _is_critical_ns_record(self, values):
        """
        检查记录是否为 DNSPod 系统核心 NS 记录
        values: 列表，顺序为 [ID, 子域名, 类型, 记录值, TTL, 线路, 状态, 备注]
        返回 True 表示是核心记录，应禁止删除/修改
        """
        if len(values) < 4:
            return False
        sub_domain = values[1]  # 子域名
        record_type = values[2]  # 类型
        record_value = values[3]  # 记录值
        # 判断条件：主机记录为 @，类型为 NS，记录值包含 .dnspod.net
        return (sub_domain == '@' and
                record_type.upper() == 'NS' and
                '.dnspod.net' in record_value.lower())

    def on_domain_selected(self, event=None):
        domain_name = self.domain_var.get()
        if not domain_name:
            return
        for d in self.domain_list:
            if d['name'] == domain_name:
                self.current_domain_id = d['id']
                self.current_domain_name = domain_name
                break
        self.refresh_records()

    def refresh_records(self):
        if not self.current_domain_id or not self.api:
            return
        try:
            records = self.api.get_record_list(self.current_domain_id)
            self.records = records
            self.tree.delete(*self.tree.get_children())

            # # 调试：打印第一条记录以便查看字段
            # if records:
            #     print("第一条记录原始数据:", records[0])

            for rec in records:
                # 解析状态
                status_val = rec.get('status', '')
                if not status_val:
                    status_val = rec.get('record_status', '')
                status_lower = str(status_val).lower()
                status_text = "启用" if status_lower in ('1', 'enable', 'enabled') else "禁用"

                # 获取备注，可能为空
                remark = rec.get('remark', '') or ''

                values = (
                    rec['id'],
                    rec['name'],
                    rec['type'],
                    rec['value'],
                    rec['ttl'],
                    rec.get('line', '默认'),
                    status_text,
                    remark
                )
                self.tree.insert("", tk.END, values=values)
            self.status.config(text=f"记录数: {len(records)}")
        except Exception as e:
            messagebox.showerror("刷新失败", str(e))

    def on_record_selected(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        item = self.tree.item(selected[0])
        values = item['values']
        if values:
            # values: ID,子域名,类型,记录值,TTL,线路,状态,备注
            self.entry_sub.delete(0, tk.END)
            self.entry_sub.insert(0, values[1])
            self.combo_type.set(values[2])
            self.entry_value.delete(0, tk.END)
            self.entry_value.insert(0, values[3])
            self.entry_ttl.delete(0, tk.END)
            self.entry_ttl.insert(0, values[4])
            # 加载备注
            self.entry_remark.delete(0, tk.END)
            self.entry_remark.insert(0, values[7])  # 备注列

    def add_record(self):
        if not self.current_domain_id or not self.api:
            return
        sub = self.entry_sub.get().strip()
        rtype = self.combo_type.get().strip()
        value = self.entry_value.get().strip()
        ttl = self.entry_ttl.get().strip()
        remark = self.entry_remark.get().strip()  # 获取备注

        if not sub or not rtype or not value or not ttl:
            messagebox.showerror("错误", "请填写完整信息")
            return
        try:
            ttl = int(ttl)
        except:
            messagebox.showerror("错误", "TTL 必须为数字")
            return

        # 1. 创建记录
        result = self.api.create_record(self.current_domain_id, sub, rtype, value, ttl)
        if result.get('status', {}).get('code') != '1':
            msg = result.get('status', {}).get('message', '未知错误')
            messagebox.showerror("添加失败", msg)
            return

        # 2. 如果备注非空，尝试设置备注
        record_id = result.get('record', {}).get('id')
        if remark and record_id:
            remark_result = self.api.set_record_remark(self.current_domain_id, record_id, remark)
            if remark_result.get('status', {}).get('code') != '1':
                # 备注设置失败，但记录已创建，给出警告
                warn_msg = f"记录已创建，但备注设置失败：{remark_result.get('status', {}).get('message', '未知错误')}\n你可以稍后手动更新备注。"
                messagebox.showwarning("部分成功", warn_msg)
            else:
                messagebox.showinfo("成功", "记录及备注添加成功")
        else:
            messagebox.showinfo("成功", "记录添加成功")

        # 刷新列表
        self.refresh_records()

    def update_record(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("错误", "请先在列表中选择要修改的记录")
            return
        item = self.tree.item(selected[0])
        values = item['values']
        # --- 保护：禁止修改核心 NS 记录 ---
        if self._is_critical_ns_record(values):
            messagebox.showerror(
                "操作被禁止",
                f"检测到系统核心 NS 记录，禁止修改！\n\n"
                f"记录详情：{values[1]} {values[2]} {values[3]}\n"
                "修改该记录将导致整个域名无法解析，所有服务中断。"
            )
            return
        record_id = values[0]
        sub = self.entry_sub.get().strip()
        rtype = self.combo_type.get().strip()
        value = self.entry_value.get().strip()
        ttl = self.entry_ttl.get().strip()
        if not sub or not rtype or not value or not ttl:
            messagebox.showerror("错误", "请填写完整信息")
            return
        try:
            ttl = int(ttl)
        except:
            messagebox.showerror("错误", "TTL 必须为数字")
            return
        result = self.api.modify_record(self.current_domain_id, record_id, sub, rtype, value, ttl)
        if result.get('status', {}).get('code') == '1':
            messagebox.showinfo("成功", "记录修改成功")
            self.refresh_records()
        else:
            msg = result.get('status', {}).get('message', '未知错误')
            messagebox.showerror("修改失败", msg)

    def delete_record(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("错误", "请先在列表中选择要删除的记录")
            return
        # 获取选中记录的详细信息
        item = self.tree.item(selected[0])
        values = item['values']

        # --- 使用辅助方法判断 ---
        if self._is_critical_ns_record(values):
            messagebox.showerror(
                "操作被禁止",
                f"检测到系统核心 NS 记录，禁止删除！\n\n"
                f"记录详情：{values[1]} {values[2]} {values[3]}\n"
                "删除该记录将导致整个域名无法解析，所有服务中断。"
            )
            return
        if not messagebox.askyesno("确认删除", f"确定要删除选中的记录吗？\n{values[1]} {values[2]} {values[3]}"):
            return
        record_id = values[0]
        result = self.api.delete_record(self.current_domain_id, record_id)
        if result.get('status', {}).get('code') == '1':
            messagebox.showinfo("成功", "记录删除成功")
            self.refresh_records()
        else:
            msg = result.get('status', {}).get('message', '未知错误')
            messagebox.showerror("删除失败", msg)

    def toggle_record_status(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("错误", "请先在列表中选择要切换状态的记录")
            return
        item = self.tree.item(selected[0])
        values = item['values']
        # --- 保护：禁止切换核心 NS 记录的状态 ---
        if self._is_critical_ns_record(values):
            messagebox.showerror(
                "操作被禁止",
                f"检测到系统核心 NS 记录，禁止切换状态！\n\n"
                f"记录详情：{values[1]} {values[2]} {values[3]}\n"
                "改变该记录状态将导致整个域名无法解析，所有服务中断。"
            )
            return
        record_id = values[0]
        current_status_text = values[6]  # 状态列
        if current_status_text == "启用":
            new_status = "disable"
            new_status_text = "禁用"
        else:
            new_status = "enable"
            new_status_text = "启用"

        if not messagebox.askyesno("确认切换", f"将记录 [{values[1]}] 状态切换为 '{new_status_text}' 吗？"):
            return

        result = self.api.set_record_status(self.current_domain_id, record_id, new_status)
        if result.get('status', {}).get('code') == '1':
            messagebox.showinfo("成功", f"记录已切换为 '{new_status_text}'")
            self.refresh_records()
        else:
            msg = result.get('status', {}).get('message', '未知错误')
            messagebox.showerror("切换失败", msg)

    def update_remark(self):
        """更新当前选中记录的备注"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("错误", "请先在列表中选择要修改备注的记录")
            return
        item = self.tree.item(selected[0])
        values = item['values']
        # --- 保护：禁止修改核心 NS 记录的备注 ---
        if self._is_critical_ns_record(values):
            messagebox.showerror(
                "操作被禁止",
                f"检测到系统核心 NS 记录，禁止修改备注！\n\n"
                f"记录详情：{values[1]} {values[2]} {values[3]}\n"
                "该记录为域名解析的核心配置，不允许修改任何属性。"
            )
            return
        record_id = values[0]
        new_remark = self.entry_remark.get().strip()

        # 确认对话框
        if not messagebox.askyesno("确认修改", f"将记录 [{values[1]}] 的备注修改为:\n{new_remark or '(空)'}"):
            return

        result = self.api.set_record_remark(self.current_domain_id, record_id, new_remark)
        if result.get('status', {}).get('code') == '1':
            messagebox.showinfo("成功", "备注更新成功")
            self.refresh_records()
        else:
            msg = result.get('status', {}).get('message', '未知错误')
            messagebox.showerror("更新失败", msg)


if __name__ == "__main__":
    root = tk.Tk()
    app = Application(root)
    root.mainloop()