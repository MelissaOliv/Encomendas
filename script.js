document.addEventListener('DOMContentLoaded', function() {
    // Inicializa a aba correta
    if (document.querySelector('.tab-btn.active')) {
        const activeTabId = document.querySelector('.tab-btn.active').getAttribute('onclick').match(/abrirTab\('(.+)'\)/)[1];
        abrirTab(activeTabId);
    } else {
        // Se nenhuma aba estiver ativa (usuário comum), abre "Meus Pedidos"
        abrirTab('meus-pedidos');
    }
});

function abrirTab(tabId) {
    // Esconde todas as abas
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove a classe active de todos os botões
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Ativa a aba selecionada
    const tab = document.getElementById(tabId);
    if (tab) {
        tab.classList.add('active');
        const btn = document.querySelector(`.tab-btn[onclick="abrirTab('${tabId}')"]`);
        if (btn) btn.classList.add('active');
    }

    // Carrega os dados necessários
    if (tabId === 'meus-pedidos') carregarMeusPedidos();
    if (tabId === 'todos-pedidos') carregarTodosPedidos();
}

// Formulário de novo pedido (só aparece para admin)
document.getElementById('form-pedido')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const pedido = {
        cliente: document.getElementById('cliente').value,
        itens: document.getElementById('itens').value,
        observacoes: document.getElementById('observacoes').value
    };

    try {
        const response = await fetch('/pedidos/novo', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(pedido)
        });
        
        if (response.status === 403) {
            alert('Acesso não autorizado!');
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            alert('Pedido criado com sucesso!');
            document.getElementById('form-pedido').reset();
            abrirChat(data.pedido_id);
        }
    } catch (error) {
        console.error('Erro:', error);
    }
});

// Carregar pedidos
async function carregarMeusPedidos() {
    try {
        const response = await fetch('/pedidos');
        const pedidos = await response.json();
        
        const container = document.getElementById('lista-meus-pedidos');
        container.innerHTML = '';
        
        if (pedidos.length === 0) {
            container.innerHTML = '<p>Nenhum pedido encontrado.</p>';
            return;
        }
        
        pedidos.forEach(pedido => {
            const card = document.createElement('div');
            card.className = 'pedido-card';
            card.innerHTML = `
                <h3>Pedido #${pedido.id} - ${pedido.cliente}</h3>
                <p><strong>Status:</strong> <span class="status-${pedido.status}">${pedido.status}</span></p>
                <p><strong>Data:</strong> ${new Date(pedido.data_criacao).toLocaleString()}</p>
                <button onclick="abrirChat(${pedido.id})">Abrir Chat</button>
            `;
            container.appendChild(card);
        });
    } catch (error) {
        console.error('Erro:', error);
    }
}

async function carregarTodosPedidos() {
    try {
        const response = await fetch('/pedidos');
        const pedidos = await response.json();
        
        const container = document.getElementById('lista-todos-pedidos');
        container.innerHTML = '';
        
        if (pedidos.length === 0) {
            container.innerHTML = '<p>Nenhum pedido encontrado.</p>';
            return;
        }
        
        pedidos.forEach(pedido => {
            const card = document.createElement('div');
            card.className = 'pedido-card';
            card.innerHTML = `
                <h3>Pedido #${pedido.id} - ${pedido.cliente}</h3>
                <p><strong>Criado por:</strong> ${pedido.criador}</p>
                <p><strong>Status:</strong> <span class="status-${pedido.status}">${pedido.status}</span></p>
                <p><strong>Data:</strong> ${new Date(pedido.data_criacao).toLocaleString()}</p>
                <button onclick="abrirChat(${pedido.id})">Abrir Chat</button>
            `;
            container.appendChild(card);
        });
    } catch (error) {
        console.error('Erro:', error);
    }
}

// Chat
let pedidoAtual = null;
let chatInterval = null;

function abrirChat(pedidoId) {
    pedidoAtual = pedidoId;
    document.getElementById('chat-pedido-id').textContent = `#${pedidoId}`;
    document.getElementById('chat-modal').style.display = 'flex';
    carregarMensagens();
    
    // Atualiza mensagens a cada 3 segundos
    if (chatInterval) clearInterval(chatInterval);
    chatInterval = setInterval(carregarMensagens, 3000);
}

function fecharChat() {
    document.getElementById('chat-modal').style.display = 'none';
    if (chatInterval) clearInterval(chatInterval);
}

async function carregarMensagens() {
    if (!pedidoAtual) return;
    
    try {
        const response = await fetch(`/chat/${pedidoAtual}/mensagens`);
        const mensagens = await response.json();
        
        const container = document.getElementById('chat-messages');
        container.innerHTML = '';
        
        // Obter o ID do usuário atual
        const usuarioAtualId = window.usuarioAtualId;
        
        mensagens.forEach(msg => {
            const msgElement = document.createElement('div');
            msgElement.className = `message ${msg.usuario_id === usuarioAtualId ? 'sent' : 'received'}`;
            msgElement.innerHTML = `
                <strong>${msg.usuario_nome}</strong>
                <p>${msg.texto}</p>
                <small>${new Date(msg.data).toLocaleString()}</small>
            `;
            container.appendChild(msgElement);
        });
        
        container.scrollTop = container.scrollHeight;
    } catch (error) {
        console.error('Erro:', error);
    }
}

document.getElementById('form-mensagem').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const texto = document.getElementById('mensagem-texto').value.trim();
    
    if (texto && pedidoAtual) {
        try {
            const response = await fetch(`/chat/${pedidoAtual}/mensagens`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `texto=${encodeURIComponent(texto)}`
            });
            
            if (response.ok) {
                document.getElementById('mensagem-texto').value = '';
                carregarMensagens();
            }
        } catch (error) {
            console.error('Erro:', error);
        }
    }
});

// Fechar modal ao clicar no X
document.querySelector('.close')?.addEventListener('click', fecharChat);

// Fechar modal ao clicar fora
window.addEventListener('click', function(event) {
    if (event.target === document.getElementById('chat-modal')) {
        fecharChat();
    }
});