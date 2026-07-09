/**
 * LS 桥接书签 v2 — 简化版
 *
 * 在 LS 标注页面点击书签后：
 * 1. 从 URL 提取 LS 地址、项目 ID
 * 2. 通过 LS API 拉取 caption_v5_translate
 * 3. POST 到本地桥接服务器
 * 4. 编辑器从服务器拉取数据
 */
(function () {
  var SERVER = 'http://127.0.0.1:8000';
  var path = window.location.pathname;
  // 用 indexOf 替代正则，避免编码问题
  if (path.indexOf('/projects/') < 0) { alert('当前页面不是LS项目页'); return; }
  var projectId = path.split('/projects/')[1].split('/')[0];
  if (!projectId) { alert('无法识别项目ID'); return; }
  var taskId = '';
  try { var sp = new URL(window.location.href).searchParams; taskId = sp.get('task') || sp.get('selected') || ''; } catch (e) {}
  var token = localStorage.getItem('ls_bridge_token');
  if (!token) {
    token = prompt('请输入LS API Token（只需输入一次，自动保存）:\n\n可以在LS页面右上角头像 → Account → Access Token 找到');
    if (!token) return;
    localStorage.setItem('ls_bridge_token', token);
  }
  var xhr = new XMLHttpRequest();
  xhr.open('GET', window.location.origin + '/api/tasks/?project=' + projectId + '&page=1&page_size=100', true);
  xhr.setRequestHeader('Authorization', 'Token ' + token);
  xhr.timeout = 10000;
  xhr.onload = function () {
    try {
      var data = JSON.parse(xhr.responseText);
      var tasks = data.results || data.tasks || [];
      var target = null;
      if (taskId) target = tasks.find(function (t) { return String(t.id) === taskId; }) || tasks.find(function (t) { return String(t.data && t.data.id) === taskId; });
      if (!target) target = tasks.find(function (t) { return !t.is_labeled && (!t.annotations || t.annotations.length === 0); });
      if (!target) { alert('未找到未标注任务'); return; }
      var captionText = (target.data && target.data.caption_v5_translate) || '';
      var memo = (target.data && target.data.memo) || '';
      var videoUrl = (target.data && target.data.video_url) || '';
      fetch(SERVER + '/api/bridge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ls_base: window.location.origin,
          project_id: projectId,
          task_id: target.id,
          memo: memo,
          video_url: videoUrl,
          caption_v5_translate: captionText,
          task_name: (target.data && target.data.task_name) || ''
        })
      }).then(function (r) { return r.json(); })
        .then(function (res) { alert('桥接成功!\n请到编辑器点击「从LS桥接」'); })
        .catch(function (err) { alert('桥接失败: ' + err.message + '\n请确认python3 server.py已启动'); });
    } catch (e) { alert('解析失败: ' + e.message); }
  };
  xhr.onerror = function () { alert('API请求失败，请确认LS可访问'); };
  xhr.ontimeout = function () { alert('API请求超时'); };
  xhr.send();
})();
