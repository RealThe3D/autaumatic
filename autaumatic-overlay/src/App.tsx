import { useEffect, useState } from "react";
import "./App.css";

// The backend is the source of truth; this overlay only renders what it receives.
// Host/port come from the backend's config.toml [server].
const WS_URL = "ws://127.0.0.1:8765/ws";
const SLOT_COUNT = 4;

// Mirrors the schema documented in src/messages.py.
interface Item {
  name: string;
  url_name: string | null;
  plat: number | null;
  ducats: number | null;
  confidence: number;
  known: boolean;
}

interface ScanResult {
  type: "scan_result";
  items: Item[];
}

type Message =
  | ScanResult
  | { type: "scan_started" }
  | { type: "status"; state?: string }
  | { type: "error"; message?: string };

type Status = "connected" | "scanning" | "disconnected";

const STATUS_TEXT: Record<Status, string> = {
  connected: "",
  scanning: "Scanning...",
  disconnected: "Backend disconnected",
};

function App() {
  const [items, setItems] = useState<(Item | undefined)[]>([]);
  const [status, setStatus] = useState<Status>("disconnected");

  useEffect(() => {
    let ws: WebSocket | null = null;
    let stopped = false;
    let retries = 0;
    let timer: number | undefined;

    function connect() {
      ws = new WebSocket(WS_URL);
      ws.onopen = () => {
        retries = 0;
        setStatus("connected");
      };
      ws.onmessage = (event) => {
        let msg: Message;
        try {
          msg = JSON.parse(event.data) as Message;
        } catch {
          return; // not JSON; ignore
        }
        if (msg.type === "scan_result") {
          setItems(msg.items.slice(0, SLOT_COUNT));
          setStatus("connected");
        } else if (msg.type === "scan_started") {
          setStatus("scanning");
        } else if (msg.type === "status" && msg.state === "idle") {
          setStatus("connected");
        } else if (msg.type === "error") {
          console.error("Backend error:", msg.message);
          setStatus("connected");
        }
      };
      ws.onclose = () => {
        setStatus("disconnected");
        if (!stopped) {
          // Reconnect with capped exponential backoff.
          const delay = Math.min(1000 * 2 ** retries++, 10_000);
          timer = window.setTimeout(connect, delay);
        }
      };
      ws.onerror = () => ws?.close();
    }

    connect();
    return () => {
      stopped = true;
      if (timer) clearTimeout(timer);
      ws?.close();
    };
  }, []);

  // Always render four slots; empty ones stay dim placeholders.
  const slots: (Item | undefined)[] = [];
  for (let i = 0; i < SLOT_COUNT; i++) slots.push(items[i]);

  return (
    <main className="overlay">
      {status !== "connected" && (
        <div className={`status ${status}`}>{STATUS_TEXT[status]}</div>
      )}
      <div className="slots">
        {slots.map((item, i) =>
          item ? (
            <div key={i} className={item.known ? "slot" : "slot unknown"}>
              <span className="name">{item.name}</span>
              <span className="prices">
                <span className="plat">{item.plat ?? "—"} plat</span>
                <span className="ducats">{item.ducats ?? "—"} ducats</span>
              </span>
            </div>
          ) : (
            <div key={i} className="slot empty">
              —
            </div>
          ),
        )}
      </div>
    </main>
  );
}

export default App;