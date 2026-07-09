/**
 * LS 桥接书签（注入脚本）
 *
 * 在 LS 标注页面点击书签后：
 * 1. 从 URL 提取 LS 地址、项目 ID、任务 ID
 * 2. 通过 LS API 获取 caption_v5_translate 数据
 * 3. 发送到本地桥接服务器（http://127.0.0.1:8000）
 * 4. 编辑器页面从桥接服务器拉取数据
 *
 * 使用方式：
 * 1. 复制本文件内容
 * 2. 在浏览器书签栏新建书签，名称「LS桥接」
 * 3. URL 粘贴为：javascript:(function(){ ... 压缩后的代码 ... })()
 */

(function () {
  'use strict';

  var SERVER = 'http://127.0.0.1:8000';
  var LS_BASE = window.location.origin;

  // 从 URL 提取项目 ID
  var pm = window.location.pathname.match(/\/projects\/(\d+)/);
  if (!pm) { alert('当前页面不是 LS 项目页'); return; }
  var projectId = pm[1];

  // 从 URL 提取任务 ID
  var taskId = '';
  try {
    var sp = new URL(window.location.href).searchParams;
    taskId = sp.get('task') || sp.get('selected') || '';
  } catch (e) {}

  var info = [];
  info.push('📌 已捕获当前页面信息');
  info.push('   服务器: ' + LS_BASE);
  info.push('   项目 ID: ' + projectId);
  info.push('   任务 ID: ' + (taskId || '未取到，会在API层自动查找'));

  // 需要在书签里填入你的 API Token
  var token = localStorage.getItem('ls_bridge_token');
  if (!token) {
    token = prompt('请输入 LS API Token（只需输入一次，会保存在本地）:\n\n可以在 LS 页面右上角头像 → Account → Access Token 找到');
    if (!token) { alert('已取消'); return; }
    localStorage.setItem('ls_bridge_token', token);
  }

  info.push('   Token: ' + token.slice(0, 8) + '...');

  // 调用 LS API 获取任务列表
  var xhr = new XMLHttpRequest();
  var url = LS_BASE + '/api/tasks/?project=' + projectId + '&page=1&page_size=100';
  xhr.open('GET', url, true);
  xhr.setRequestHeader('Authorization', 'Token ' + token);
  xhr.timeout = 10000;

  xhr.onload = function () {
    try {
      var data = JSON.parse(xhr.responseText);
      var tasks = data.results || data.tasks || [];

      // 找第一个未标注任务
      var target = null;
      if (taskId) {
        // 优先找指定任务
        target = tasks.find(function (t) { return String(t.id) === taskId; }) || tasks.find(function (t) { return String(t.data && t.data.id) === taskId; });
      }
      if (!target) {
        target = tasks.find(function (t) { return !t.is_labeled && (!t.annotations || t.annotations.length === 0); });
      }
      if (!target) {
        info.push('❌ 未找到未标注任务');
        alert(info.join('\n'));
        return;
      }

      var captionText = (target.data && target.data.caption_v5_translate) || '';
      var memo = (target.data && target.data.memo) || '';
      var videoUrl = (target.data && target.data.video_url) || '';

      info.push('   ✅ 已获取任务 #' + target.id + ': ' + memo);
      info.push('   文本长度: ' + captionText.length + ' 字符');
      info.push('   正在发送到本地桥接服务器...');

      // 发送到本地桥接服务器
      fetch(SERVER + '/api/bridge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ls_base: LS_BASE,
          project_id: projectId,
          task_id: target.id,
          memo: memo,
          video_url: videoUrl,
          caption_v5_translate: captionText,
          task_name: target.data && target.data.task_name || ''
        })
      }).then(function (r) { return r.json(); }).then(function (res) {
        info.push('   ✅ 桥接成功！请到编辑器点击「📥 从LS桥接」');
        alert(info.join('\n'));
      }).catch(function (err) {
        info.push('   ❌ 桥接失败: ' + err.message);
        info.push('     请确认编辑器服务器已启动（python3 server.py）');
        alert(info.join('\n'));
      });

    } catch (e) {
      alert('解析数据失败: ' + e.message);
    }
  };

  xhr.onerror = function () {
    // 如果跨域失败，把信息复制到剪贴板 fallback
    var fallbackText = JSON.stringify({
      ls_base: LS_BASE,
      project_id: projectId,
      task_id: taskId,
      token: token
    });
    try {
      navigator.clipboard.writeText(fallbackText);
    } catch(e) {}
    alert('❌ 无法直接调用 API（可能是跨域限制）\n请确认 LS 服务器允许跨域访问。');
  };

  xhr.ontimeout = function () {
    alert('❌ API 请求超时，请检查网络连接');
  };

  xhr.send();
})();
